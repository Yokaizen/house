"""Authentification (comptes locaux), sessions longues et protection CSRF."""
import hashlib
import hmac
import re
import secrets
import string
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import SessionAuth, Utilisateur
from app.services.temps import maintenant_utc, vers_utc

COOKIE = "badgeage_session"
_hasher = PasswordHasher()

MAX_ECHECS = 5
DUREE_BLOCAGE = timedelta(minutes=15)


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


# --- Sessions ----------------------------------------------------------------

def _empreinte(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authentifier(db: Session, identifiant: str, mdp: str) -> tuple[Utilisateur | None, str | None]:
    """Renvoie (utilisateur, None) si succès, (None, message) sinon."""
    identifiant = identifiant.strip()
    u = db.scalar(select(Utilisateur).where(
        or_(Utilisateur.matricule == identifiant, Utilisateur.email == identifiant.lower())))
    message = "Identifiant ou mot de passe incorrect."
    if u is None or not u.actif:
        verifier_mdp(None, mdp)
        return None, message
    if u.bloque_jusqu_a and vers_utc(u.bloque_jusqu_a) > maintenant_utc():
        return None, "Trop de tentatives. Réessayez dans quelques minutes."
    if not verifier_mdp(u.mot_de_passe_hash, mdp):
        u.echecs_connexion = (u.echecs_connexion or 0) + 1
        if u.echecs_connexion >= MAX_ECHECS:
            u.bloque_jusqu_a = maintenant_utc() + DUREE_BLOCAGE
            u.echecs_connexion = 0
        db.commit()
        return None, message
    u.echecs_connexion = 0
    u.bloque_jusqu_a = None
    u.derniere_connexion = maintenant_utc()
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
