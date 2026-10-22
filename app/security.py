"""Authentification (comptes locaux), sessions longues et protection CSRF."""
import hashlib
import hmac
import logging
import re
import secrets
import string
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import SessionAuth, TentativeConnexion, Utilisateur
from app.services.temps import maintenant_utc, vers_utc

log = logging.getLogger(__name__)

COOKIE = "badgeage_session"
_hasher = PasswordHasher()

# Limitation des tentatives de connexion, sur des fenêtres glissantes. Un compte
# n'est bloqué pour toutes les adresses qu'après des échecs venus de plusieurs
# adresses : quelqu'un qui connaît un matricule ne peut pas, à lui seul, empêcher
# le salarié de se connecter depuis son téléphone.
FENETRE = timedelta(minutes=15)
MAX_ECHECS_IP = 10  # depuis une adresse, tous identifiants confondus
MAX_ECHECS = 5  # depuis une adresse, pour un même identifiant
FENETRE_COMPTE = timedelta(hours=1)
MAX_ECHECS_COMPTE = 30  # pour un compte, toutes adresses confondues
DUREE_BLOCAGE = timedelta(minutes=15)
MESSAGE_BLOCAGE = "Trop de tentatives. Réessayez dans quelques minutes."


class NonConnecte(Exception):
    """Levée quand une page exige une connexion : redirige vers /connexion."""


class ChangementMdpRequis(Exception):
    pass


class AccesRefuse(Exception):
    pass


class CsrfInvalide(Exception):
    pass


# --- Mots de passe ---------------------------------------------------------

def hacher(mdp: str) -> str:
    return _hasher.hash(mdp)


def verifier_mdp(hash_: str | None, mdp: str) -> bool:
    if not hash_:
        return False
    try:
        return _hasher.verify(hash_, mdp)
    except (VerificationError, InvalidHashError):
        return False


def mdp_temporaire() -> str:
    """Mot de passe provisoire lisible (sans caractères ambigus)."""
    alphabet = "".join(c for c in string.ascii_letters + string.digits if c not in "0OoIl1")
    while True:
        mdp = "".join(secrets.choice(alphabet) for _ in range(12))
        if re.search(r"\d", mdp) and re.search(r"[A-Za-z]", mdp):
            return mdp


def erreurs_mdp(mdp: str) -> list[str]:
    erreurs = []
    if len(mdp) < 10:
        erreurs.append("10 caractères minimum")
    if not re.search(r"[A-Za-z]", mdp) or not re.search(r"\d", mdp):
        erreurs.append("au moins une lettre et un chiffre")
    return erreurs


# --- Limitation des tentatives -----------------------------------------------

def adresse_client(request: Request) -> str:
    """Adresse IP du client. Derrière le proxy, uvicorn la lit dans X-Forwarded-For
    (gunicorn --forwarded-allow-ips) : le proxy doit donc écraser cet en-tête, pas
    le compléter, sans quoi le client choisirait l'adresse qui lui est comptée."""
    return request.client.host if request.client else "inconnue"


def _echecs(db: Session, depuis: datetime, **filtres) -> int:
    requete = select(func.count()).select_from(TentativeConnexion).where(TentativeConnexion.horodatage >= depuis)
    for colonne, valeur in filtres.items():
        requete = requete.where(getattr(TentativeConnexion, colonne) == valeur)
    return db.scalar(requete)


def debloquer(db: Session, u: Utilisateur) -> None:
    """Efface le blocage et les échecs de connexion d'un compte (réinitialisation par un administrateur)."""
    u.bloque_jusqu_a = None
    db.execute(delete(TentativeConnexion).where(TentativeConnexion.utilisateur_id == u.id))


# --- Sessions ----------------------------------------------------------------

def _empreinte(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authentifier(db: Session, identifiant: str, mdp: str, ip: str) -> tuple[Utilisateur | None, str | None]:
    """Renvoie (utilisateur, None) si succès, (None, message) sinon."""
    identifiant = identifiant.strip()
    cle = identifiant.lower()[:200]
    maintenant = maintenant_utc()
    if (_echecs(db, maintenant - FENETRE, adresse_ip=ip) >= MAX_ECHECS_IP
            or _echecs(db, maintenant - FENETRE, adresse_ip=ip, identifiant=cle) >= MAX_ECHECS):
        return None, MESSAGE_BLOCAGE
    u = db.scalar(select(Utilisateur).where(
        or_(Utilisateur.matricule == identifiant, Utilisateur.email == cle)))
    if u is not None and u.bloque_jusqu_a and vers_utc(u.bloque_jusqu_a) > maintenant:
        return None, MESSAGE_BLOCAGE
    if u is None or not u.actif or not verifier_mdp(u.mot_de_passe_hash, mdp):
        db.add(TentativeConnexion(horodatage=maintenant, adresse_ip=ip, identifiant=cle,
                                  utilisateur_id=u.id if u else None))
        db.flush()
        if _echecs(db, maintenant - FENETRE, adresse_ip=ip) == MAX_ECHECS_IP:
            log.warning("Connexions bloquées depuis %s : %s échecs en %s min", ip, MAX_ECHECS_IP,
                        FENETRE.seconds // 60)
        if u is not None and _echecs(db, maintenant - FENETRE_COMPTE, utilisateur_id=u.id) >= MAX_ECHECS_COMPTE:
            u.bloque_jusqu_a = maintenant + DUREE_BLOCAGE
            log.warning("Compte %s bloqué %s min : trop d'échecs de connexion depuis plusieurs adresses",
                        u.matricule, DUREE_BLOCAGE.seconds // 60)
        db.commit()
        return None, "Identifiant ou mot de passe incorrect."
    # Les erreurs de saisie du salarié lui-même ne comptent plus ; celles venues d'ailleurs restent.
    db.execute(delete(TentativeConnexion).where(TentativeConnexion.adresse_ip == ip,
                                                TentativeConnexion.identifiant == cle))
    u.bloque_jusqu_a = None
    u.derniere_connexion = maintenant
    if _hasher.check_needs_rehash(u.mot_de_passe_hash):
        u.mot_de_passe_hash = hacher(mdp)
    db.commit()
    return u, None


def ouvrir_session(db: Session, u: Utilisateur, user_agent: str | None, longue: bool) -> tuple[str, int | None]:
    """Crée une session ; renvoie (token, max_age du cookie)."""
    s = get_settings()
    token = secrets.token_urlsafe(32)
    duree = timedelta(days=s.session_duree_jours) if longue else timedelta(hours=12)
    db.add(SessionAuth(token_hash=_empreinte(token), csrf_token=secrets.token_urlsafe(24), utilisateur_id=u.id,
                       expire_le=maintenant_utc() + duree, user_agent=(user_agent or "")[:300]))
    db.commit()
    return token, int(duree.total_seconds()) if longue else None


def fermer_session(db: Session, token: str | None) -> None:
    if token:
        db.query(SessionAuth).filter(SessionAuth.token_hash == _empreinte(token)).delete()
        db.commit()


def fermer_toutes_sessions(db: Session, utilisateur_id: int, sauf: int | None = None) -> None:
    q = db.query(SessionAuth).filter(SessionAuth.utilisateur_id == utilisateur_id)
    if sauf:
        q = q.filter(SessionAuth.id != sauf)
    q.delete()


def session_courante(request: Request, db: Session = Depends(get_db)) -> SessionAuth | None:
    if "session_auth" in request.state._state:
        return request.state.session_auth
    token = request.cookies.get(COOKIE)
    sess = None
    if token:
        sess = db.scalar(select(SessionAuth).where(SessionAuth.token_hash == _empreinte(token)))
        if sess and (vers_utc(sess.expire_le) < maintenant_utc() or not sess.utilisateur.actif):
            db.delete(sess)
            db.commit()
            sess = None
        elif sess and maintenant_utc() - vers_utc(sess.vu_le) > timedelta(hours=1):
            sess.vu_le = maintenant_utc()
            db.commit()
    request.state.session_auth = sess
    return sess


def utilisateur_optionnel(sess: SessionAuth | None = Depends(session_courante)) -> Utilisateur | None:
    return sess.utilisateur if sess else None


def utilisateur_connecte_sans_mdp(sess: SessionAuth | None = Depends(session_courante)) -> Utilisateur:
    """Connecté, même si un changement de mot de passe est en attente."""
    if sess is None:
        raise NonConnecte()
    return sess.utilisateur


def utilisateur_connecte(u: Utilisateur = Depends(utilisateur_connecte_sans_mdp)) -> Utilisateur:
    if u.doit_changer_mdp:
        raise ChangementMdpRequis()
    return u


def exiger_role(*roles: str):
    def dependance(u: Utilisateur = Depends(utilisateur_connecte)) -> Utilisateur:
        if u.role not in roles:
            raise AccesRefuse()
        return u
    return dependance


exiger_admin = exiger_role("admin")
exiger_vue_globale = exiger_role("admin", "rh")


async def verifier_csrf(request: Request, sess: SessionAuth | None = Depends(session_courante)) -> None:
    if sess is None:
        raise NonConnecte()
    jeton = request.headers.get("x-csrf-token")
    if not jeton:
        form = await request.form()
        jeton = form.get("csrf_token")
    if not jeton or not hmac.compare_digest(str(jeton), sess.csrf_token):
        raise CsrfInvalide()
