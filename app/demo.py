"""Données fictives pour le kit de démonstration (docker-compose.demo.yml).

    python -m app.demo            charge les données si la base est vide
    python -m app.demo --forcer   vide la base puis recharge les données

Ne jamais lancer sur la base de production.
"""
import os
import sys
from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Audit, Etablissement, Parametre, Pointage, SessionAuth, Utilisateur
from app.security import hacher
from app.services.temps import aujourd_hui, local_vers_utc

MOT_DE_PASSE = "Proximy2026"

# Positions de démonstration : centre approximatif de chaque commune, pas l'adresse réelle des agences.
AGENCES = [
    ("STAINS", "Stains", "93240", "Stains", 48.9497, 2.3833),
    ("GENNEVILLIERS", "Gennevilliers", "92230", "Gennevilliers", 48.9333, 2.3000),
    ("BUC", "Buc", "78530", "Buc", 48.7717, 2.1250),
    ("CRETEIL", "Créteil", "94000", "Créteil", 48.7904, 2.4556),
    ("FITZJAMES", "Fitz-James", "60600", "Fitz-James", 49.3917, 2.4317),
    ("TEST", "Agence test (à placer sur votre bureau)", None, None, None, None),
]

# matricule, nom, prénom, rôle, agence, matricule du manager, contrat, télétravail
UTILISATEURS = [
    ("ADMIN", "Démo", "Admin", "admin", None, None, "35", False),
    ("RH01", "Démo", "Rh", "rh", None, None, "35", False),
    ("M001", "Lefèvre", "Sophie", "manager", "STAINS", None, "35", False),
    ("S001", "Bernard", "Lucas", "salarie", "STAINS", "M001", "35", True),
    ("S002", "Moreau", "Inès", "salarie", "STAINS", "M001", "35", False),
    ("S003", "Garcia", "Hugo", "salarie", "STAINS", "M001", "24.5", False),
    ("S004", "Roux", "Chloé", "salarie", "CRETEIL", None, "35", False),
]


def vider(db: Session) -> None:
    for table in (Pointage, SessionAuth, Audit, Parametre):
        db.execute(delete(table))
    db.query(Utilisateur).update({"manager_id": None})
    db.execute(delete(Utilisateur))
    db.execute(delete(Etablissement))
    db.commit()


def charger(db: Session) -> None:
    agences = {}
    for code, nom, cp, ville, lat, lon in AGENCES:
        e = Etablissement(code=code, nom=nom, code_postal=cp, ville=ville, latitude=lat, longitude=lon, rayon_m=100)
        db.add(e)
        agences[code] = e
    db.flush()

    u: dict[str, Utilisateur] = {}
    for mat, nom, prenom, role, agence, manager, heures, teletravail in UTILISATEURS:
        x = Utilisateur(
            matricule=mat, nom=nom, prenom=prenom, role=role, email=f"{mat.lower()}@demo.invalid",
            etablissement_id=agences[agence].id if agence else None,
            manager_id=u[manager].id if manager else None, heures_hebdo=Decimal(heures),
            teletravail_autorise=teletravail, mot_de_passe_hash=hacher(MOT_DE_PASSE), doit_changer_mdp=False,
        )
        db.add(x)
        db.flush()
        u[mat] = x
    # Domicile de démonstration de Lucas (télétravail), à 2 km de l'agence de Stains.
    u["S001"].ville, u["S001"].code_postal = "Pierrefitte-sur-Seine", "93380"
    u["S001"].domicile_lat, u["S001"].domicile_lon = 48.9650, 2.3610

    _badgeages(db, u)
    db.commit()


def _badgeages(db: Session, u: dict[str, Utilisateur]) -> None:
    """Six semaines de badgeages jusqu'à hier, avec les cas particuliers à montrer."""
    def ajout(mat, type_, jour: date, h, mi=0, **kw):
        kw.setdefault("zone_statut", "dans_zone")
        kw.setdefault("appareil", "mobile")
        kw.setdefault("precision_m", 12)
        db.add(Pointage(utilisateur_id=u[mat].id, type=type_, horodatage=local_vers_utc(jour, time(h, mi)),
                        cree_par_id=u[mat].id, **kw))

    hier = aujourd_hui() - timedelta(days=1)
    debut = hier - timedelta(days=41)
    ouvres = [debut + timedelta(days=i) for i in range(42) if (debut + timedelta(days=i)).weekday() < 5]
    for n, j in enumerate(ouvres):
        # Lucas : journée, un oubli saisi a posteriori et quelques départs hors zone.
        ajout("S001", "entree", j, 8, (n * 7) % 20)
        if n == 21:
            ajout("S001", "sortie", j, 17, 5, source="manuel", zone_statut="non_applicable", appareil=None,
                  precision_m=None, motif="Téléphone déchargé")
        else:
            ajout("S001", "sortie", j, 16, 30 + n % 20, zone_statut="hors_zone" if n % 11 == 3 else "dans_zone")
        # Chloé : un badgeage avec position refusée.
        ajout("S004", "entree", j, 7, 55, zone_statut="indisponible" if n == 7 else "dans_zone",
              precision_m=None if n == 7 else 20)
        ajout("S004", "sortie", j, 15, 40)

    # Inès : postes de nuit du lundi au jeudi, badgés depuis un ordinateur. Dernière arrivée
    # avant-hier, pour que le départ du lendemain ne tombe pas dans le futur.
    for n, j in enumerate(x for x in ouvres if x.weekday() < 4 and x < hier):
        ajout("S002", "entree", j, 21, 45, appareil="ordinateur", precision_m=60)
        ajout("S002", "sortie", j + timedelta(days=1), 5, 30, appareil="ordinateur", precision_m=420,
              zone_statut="indetermine" if n % 9 == 2 else "dans_zone")

    # Hugo : temps partiel (lundi, mardi, jeudi), une journée longue et un départ oublié.
    for n, j in enumerate(x for x in ouvres if x.weekday() in (0, 1, 3)):
        ajout("S003", "entree", j, 7 if n == 4 else 9)
        if n != 10:
            ajout("S003", "sortie", j, 19 if n == 4 else 17, 15)


def main(args: list[str]) -> int:
    if os.environ.get("DEMO") != "1":
        print("Refusé : ce script ne s'exécute qu'avec DEMO=1 (kit de démonstration).")
        return 1
    forcer = "--forcer" in args
    with SessionLocal() as db:
        deja = db.scalar(select(Utilisateur.id).limit(1)) is not None
        if deja and not forcer:
            print("Base déjà remplie : données de démonstration conservées.")
            return 0
        if deja:
            vider(db)
        charger(db)
    print("Données de démonstration chargées.")
    print(f"Identifiants : ADMIN, RH01, M001, S001 à S004. Mot de passe : {MOT_DE_PASSE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
