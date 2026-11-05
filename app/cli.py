"""Commandes d'exploitation.

    python -m app.cli creer-admin MATRICULE NOM PRENOM [EMAIL]
    python -m app.cli creer-etablissement CODE "NOM"
"""
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Etablissement, Utilisateur
from app.security import debloquer, hacher, mdp_temporaire


def creer_admin(matricule: str, nom: str, prenom: str, email: str | None = None) -> None:
    with SessionLocal() as db:
        u = db.scalar(select(Utilisateur).where(Utilisateur.matricule == matricule))
        mdp = mdp_temporaire()
        if u is None:
            u = Utilisateur(matricule=matricule, nom=nom, prenom=prenom, email=(email or "").lower() or None)
            db.add(u)
        u.role, u.actif = "admin", True
        u.mot_de_passe_hash, u.doit_changer_mdp = hacher(mdp), True
        db.flush()
        debloquer(db, u)
        db.commit()
    print(f"Administrateur {matricule} prêt. Mot de passe provisoire : {mdp}")
    print("Il devra être changé à la première connexion.")


def creer_etablissement(code: str, nom: str) -> None:
    with SessionLocal() as db:
        if db.scalar(select(Etablissement).where(Etablissement.code == code.upper())):
            print(f"L'établissement {code.upper()} existe déjà.")
            return
        db.add(Etablissement(code=code.upper(), nom=nom))
        db.commit()
    print(f"Établissement {code.upper()} créé. Renseignez son adresse dans l'administration pour le localiser.")


def main(args: list[str]) -> int:
    if len(args) >= 4 and args[0] == "creer-admin":
        creer_admin(*args[1:5])
        return 0
    if len(args) == 3 and args[0] == "creer-etablissement":
        creer_etablissement(args[1], args[2])
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
