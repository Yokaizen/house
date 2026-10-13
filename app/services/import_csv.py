"""Import des utilisateurs par fichier CSV (création ou mise à jour par matricule)."""
import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ROLES, Etablissement, Utilisateur
from app.security import hacher, mdp_temporaire
from app.services.audit import instantane, journaliser
from app.services.geocodage import adresse_texte, geocoder
from app.services.temps import aujourd_hui

COLONNES = [
    "matricule", "nom", "prenom", "email", "etablissement", "matricule_manager", "role", "heures_hebdo",
    "teletravail", "adresse_numero", "adresse_voie", "adresse_complement", "code_postal", "ville", "date_sortie",
]
OBLIGATOIRES = {"matricule", "nom", "prenom"}
EXEMPLE = [
    ["A0001", "Martin", "Julie", "julie.martin@proximy.net", "STAINS", "", "manager", "35", "oui",
     "12", "rue de la Paix", "Bâtiment B", "93240", "Stains", ""],
    ["A0002", "Durand", "Karim", "karim.durand@proximy.net", "STAINS", "A0001", "salarie", "35", "oui",
     "4", "allée des Tilleuls", "", "93240", "Stains", ""],
]
_CHAMPS_ADRESSE = ("adresse_numero", "adresse_voie", "adresse_complement", "code_postal", "ville")


@dataclass
class Rapport:
    crees: int = 0
    mis_a_jour: int = 0
    erreurs: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    identifiants: list[tuple[str, str, str]] = field(default_factory=list)  # matricule, nom, mot de passe

    @property
    def total(self) -> int:
        return self.crees + self.mis_a_jour


def modele_csv() -> str:
    flux = io.StringIO()
    w = csv.writer(flux, delimiter=";")
    w.writerow(COLONNES)
    w.writerows(EXEMPLE)
    return flux.getvalue()


def _decoder(contenu: bytes) -> str:
    for encodage in ("utf-8-sig", "cp1252"):
        try:
            return contenu.decode(encodage)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encodage du fichier non reconnu (enregistrez-le en UTF-8 ou CSV Windows).")


def _oui(v: str) -> bool | None:
    v = v.strip().lower()
    if v in ("oui", "o", "1", "true", "vrai", "x", "yes"):
        return True
    if v in ("non", "n", "0", "false", "faux", "no"):
        return False
    return None


def _date(v: str) -> date | None:
    v = v.strip()
    if not v:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"date « {v} » invalide (attendu JJ/MM/AAAA)")


def importer(db: Session, contenu: bytes, acteur: Utilisateur, geocoder_adresses: bool = True) -> Rapport:
    rapport = Rapport()
    try:
        texte = _decoder(contenu)
    except ValueError as e:
        rapport.erreurs.append(str(e))
        return rapport
    premiere = texte.splitlines()[0] if texte.strip() else ""
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=";" if premiere.count(";") >= premiere.count(",") else ",")
    entetes = {(h or "").strip().lower() for h in (lecteur.fieldnames or [])}
    if manquantes := OBLIGATOIRES - entetes:
        rapport.erreurs.append("Colonnes obligatoires manquantes : " + ", ".join(sorted(manquantes)))
        return rapport

    etablissements = {}
    for e in db.scalars(select(Etablissement)):
        etablissements[e.code.lower()] = e
        etablissements[e.nom.lower()] = e

    liens_manager: list[tuple[Utilisateur, str, int]] = []
    vus: set[str] = set()
    for num, brut in enumerate(lecteur, start=2):
        ligne = {(k or "").strip().lower(): (v or "").strip() for k, v in brut.items() if k}
        if not any(ligne.values()):
            continue
        try:
            u = _traiter_ligne(db, ligne, etablissements, rapport, num, vus, geocoder_adresses, acteur)
        except ValueError as e:
            rapport.erreurs.append(f"Ligne {num} : {e}")
            continue
        if "matricule_manager" in ligne:
            liens_manager.append((u, ligne["matricule_manager"], num))

    db.flush()
    for u, mat_manager, num in liens_manager:
        if not mat_manager:
            u.manager_id = None
            continue
        m = db.scalar(select(Utilisateur).where(Utilisateur.matricule == mat_manager))
        if m is None:
            rapport.avertissements.append(f"Ligne {num} : manager « {mat_manager} » introuvable, lien ignoré.")
        elif m.id == u.id or _cree_un_cycle(db, u.id, m):
            rapport.avertissements.append(f"Ligne {num} : lien manager « {mat_manager} » circulaire, ignoré.")
        else:
            u.manager_id = m.id
    db.commit()
    return rapport


def _cree_un_cycle(db: Session, uid: int, manager: Utilisateur) -> bool:
    courant, vus = manager, set()
    while courant is not None and courant.id not in vus:
        if courant.manager_id == uid:
            return True
        vus.add(courant.id)
        courant = db.get(Utilisateur, courant.manager_id) if courant.manager_id else None
    return False


def _traiter_ligne(db: Session, ligne: dict, etablissements: dict, rapport: Rapport, num: int, vus: set,
                   geocoder_adresses: bool, acteur: Utilisateur) -> Utilisateur:
    matricule = ligne.get("matricule", "")
    if not matricule or not ligne.get("nom") or not ligne.get("prenom"):
        raise ValueError("matricule, nom et prénom sont obligatoires")
    if matricule in vus:
        raise ValueError(f"matricule « {matricule} » en double dans le fichier")
    vus.add(matricule)

    role = (ligne.get("role") or "salarie").lower().replace("é", "e")
    if role not in ROLES:
        raise ValueError(f"rôle « {ligne.get('role')} » inconnu (salarie, manager, rh, admin)")
    email = (ligne.get("email") or "").lower() or None
    if email and "@" not in email:
        raise ValueError(f"e-mail « {email} » invalide")
    heures = None
    if ligne.get("heures_hebdo"):
        try:
            heures = Decimal(ligne["heures_hebdo"].replace(",", "."))
        except InvalidOperation:
            raise ValueError(f"heures_hebdo « {ligne['heures_hebdo']} » invalide") from None
        if not 0 < heures <= 60:
            raise ValueError("heures_hebdo doit être compris entre 0 et 60")
    etab = None
    if ligne.get("etablissement"):
        etab = etablissements.get(ligne["etablissement"].lower())
        if etab is None:
            raise ValueError(f"établissement « {ligne['etablissement']} » inconnu (créez-le d'abord)")
    date_sortie = _date(ligne.get("date_sortie", ""))

    u = db.scalar(select(Utilisateur).where(Utilisateur.matricule == matricule))
    if email:
        requete = select(Utilisateur).where(func.lower(Utilisateur.email) == email)
        if u is not None:
            requete = requete.where(Utilisateur.id != u.id)
        if doublon := db.scalar(requete):
            raise ValueError(f"e-mail « {email} » déjà utilisé par {doublon.matricule}")

    nouveau = u is None
    avant = None if nouveau else instantane(u)
    if nouveau:
        u = Utilisateur(matricule=matricule)
        mdp = mdp_temporaire()
        u.mot_de_passe_hash = hacher(mdp)
        u.doit_changer_mdp = True
        db.add(u)
        rapport.identifiants.append((matricule, f"{ligne['prenom']} {ligne['nom']}", mdp))

    adresse_avant = tuple(getattr(u, c) or "" for c in _CHAMPS_ADRESSE)
    u.nom, u.prenom, u.role = ligne["nom"], ligne["prenom"], role
    if "email" in ligne:
        u.email = email
    if etab is not None or "etablissement" in ligne:
        u.etablissement_id = etab.id if etab else None
    if heures is not None:
        u.heures_hebdo = heures
    if (t := _oui(ligne.get("teletravail", ""))) is not None:
        u.teletravail_autorise = t
    for c in _CHAMPS_ADRESSE:
        if c in ligne:
            setattr(u, c, ligne[c] or None)
    if "date_sortie" in ligne:
        u.date_sortie = date_sortie
        u.actif = not (date_sortie and date_sortie < aujourd_hui())

    adresse_apres = tuple(getattr(u, c) or "" for c in _CHAMPS_ADRESSE)
    if adresse_apres != adresse_avant or (not u.domicile_localise and any(adresse_apres)):
        u.domicile_lat = u.domicile_lon = None
        if geocoder_adresses and u.adresse_voie and u.ville:
            r = geocoder(adresse_texte(u.adresse_numero, u.adresse_voie, u.code_postal, u.ville), u.code_postal)
            if r and r.score >= 0.5:
                u.domicile_lat, u.domicile_lon = r.latitude, r.longitude
                if r.score < 0.7:
                    rapport.avertissements.append(
                        f"Ligne {num} : adresse de {matricule} géocodée avec une confiance faible "
                        f"({r.libelle}). Vérifiez-la sur la carte.")
            else:
                rapport.avertissements.append(
                    f"Ligne {num} : adresse de {matricule} non trouvée. Saisissez la position sur la carte.")

    db.flush()
    journaliser(db, acteur, "import_creation" if nouveau else "import_mise_a_jour", "utilisateur", u.id,
                avant, instantane(u))
    if nouveau:
        rapport.crees += 1
    else:
        rapport.mis_a_jour += 1
    return u
