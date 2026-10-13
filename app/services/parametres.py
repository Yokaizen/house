"""Règles métier paramétrables depuis l'administration.

Chaque paramètre a une valeur par défaut ici ; la valeur saisie par
l'administrateur est stockée dans la table `parametres` et prend le dessus.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Parametre


@dataclass(frozen=True)
class Definition:
    cle: str
    libelle: str
    type: type
    defaut: object
    aide: str = ""
    groupe: str = "Général"
    minimum: float | None = None
    maximum: float | None = None


DEFINITIONS: list[Definition] = [
    # Géolocalisation
    Definition("rayon_defaut_m", "Rayon de tolérance par défaut (m)", int, 100,
               "Appliqué aux nouveaux établissements et aux domiciles sans rayon propre.", "Géolocalisation", 20, 5000),
    Definition("precision_max_mobile_m", "Précision maximale acceptée sur smartphone (m)", int, 150,
               "Au-delà, le résultat est « Indéterminé » sauf si la personne est clairement hors zone.",
               "Géolocalisation", 10, 5000),
    Definition("precision_max_ordinateur_m", "Précision maximale acceptée sur ordinateur (m)", int, 500,
               "Les ordinateurs se localisent par Wi-Fi ou par adresse IP, souvent moins précisément.",
               "Géolocalisation", 10, 20000),
    Definition("tous_sites_autorises", "Tous les établissements sont des lieux autorisés", bool, True,
               "Si décoché, seul l'établissement de rattachement (et le domicile) est autorisé.", "Géolocalisation"),

    # Badgeage
    Definition("paires_max_par_jour", "Nombre maximal d'arrivées par jour", int, 1,
               "1 = une seule paire arrivée/départ. Passer à 2 ou plus pour autoriser une pause badgée.",
               "Badgeage", 1, 10),
    Definition("duree_max_poste_h", "Durée maximale d'un poste (h)", int, 16,
               "Une arrivée sans départ au-delà de ce délai est considérée comme un oubli de départ.",
               "Badgeage", 4, 24),
    Definition("relance_oubli_depart_h", "Relance e-mail si pas de départ après (h)", int, 12,
               "0 pour désactiver la relance.", "Badgeage", 0, 24),

    # Saisie manuelle
    Definition("saisie_manuelle_jours_max", "Saisie manuelle : nombre de jours en arrière autorisés", int, 7,
               "", "Saisie manuelle", 0, 60),
    Definition("validation_manager", "Les saisies manuelles doivent être validées par le manager", bool, False,
               "Si activé, les saisies manuelles sont « en attente » jusqu'à validation.", "Saisie manuelle"),

    # Managers
    Definition("perimetre_manager_niveaux", "Visibilité des managers (niveaux hiérarchiques)", int, 1,
               "1 = collaborateurs directs (N-1). 2 = également les N-2.", "Managers", 1, 2),
    Definition("manager_peut_corriger", "Les managers peuvent corriger les badgeages de leur équipe", bool, True,
               "", "Managers"),

    # Alertes
    Definition("alerte_duree_jour_h", "Alerte durée journalière supérieure à (h)", float, 10.0, "", "Alertes", 1, 24),
    Definition("alerte_amplitude_h", "Alerte amplitude journalière supérieure à (h)", float, 13.0, "", "Alertes", 1, 24),
    Definition("alerte_repos_quotidien_h", "Alerte repos entre deux postes inférieur à (h)", float, 11.0, "", "Alertes", 0, 24),
    Definition("alerte_duree_semaine_h", "Alerte durée hebdomadaire supérieure à (h)", float, 48.0, "", "Alertes", 1, 80),

    # Conservation
    Definition("retention_pointages_mois", "Conservation des badgeages (mois)", int, 12,
               "Les badgeages et le journal d'audit plus anciens sont supprimés automatiquement.",
               "Conservation des données", 1, 120),
    Definition("retention_comptes_sortis_mois", "Conservation des comptes après la date de sortie (mois)", int, 2,
               "Le compte et tous ses badgeages sont supprimés après ce délai.", "Conservation des données", 0, 120),
]

_PAR_CLE = {d.cle: d for d in DEFINITIONS}


def definition(cle: str) -> Definition:
    return _PAR_CLE[cle]


def groupes() -> dict[str, list[Definition]]:
    """Définitions regroupées, dans l'ordre de déclaration."""
    res: dict[str, list[Definition]] = {}
    for d in DEFINITIONS:
        res.setdefault(d.groupe, []).append(d)
    return res


def lire(db: Session, cle: str):
    d = _PAR_CLE[cle]
    p = db.get(Parametre, cle)
    if p is None or p.valeur is None:
        return d.defaut
    try:
        return d.type(p.valeur)
    except (TypeError, ValueError):
        return d.defaut


def tous(db: Session) -> dict:
    stockes = {p.cle: p.valeur for p in db.query(Parametre).all()}
    resultat = {}
    for d in DEFINITIONS:
        v = stockes.get(d.cle, d.defaut)
        try:
            resultat[d.cle] = d.type(v) if v is not None else d.defaut
        except (TypeError, ValueError):
            resultat[d.cle] = d.defaut
    return resultat


def convertir(cle: str, brut: str | None):
    """Convertit une saisie de formulaire ; lève ValueError si invalide."""
    d = _PAR_CLE[cle]
    if d.type is bool:
        return brut in ("on", "true", "1", "oui")
    if brut is None or brut.strip() == "":
        raise ValueError(f"{d.libelle} : valeur obligatoire")
    v = d.type(brut.replace(",", "."))
    if d.minimum is not None and v < d.minimum:
        raise ValueError(f"{d.libelle} : minimum {d.minimum:g}")
    if d.maximum is not None and v > d.maximum:
        raise ValueError(f"{d.libelle} : maximum {d.maximum:g}")
    return v


def ecrire(db: Session, cle: str, valeur) -> None:
    p = db.get(Parametre, cle)
    if p is None:
        db.add(Parametre(cle=cle, valeur=valeur))
    else:
        p.valeur = valeur
