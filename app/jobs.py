"""Tâches planifiées (conteneur « worker ») : purge RGPD, désactivation des
comptes sortis, relances d'oubli de départ, rappel des saisies à valider."""
import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Audit, Parametre, Pointage, SessionAuth, Utilisateur
from app.services import parametres as P
from app.services.audit import journaliser
from app.services.mail import envoyer
from app.services.pointages import ids_equipe
from app.services.temps import aujourd_hui, ajouter_mois, debut_jour_utc, format_date, format_heure, maintenant_utc, tz

log = logging.getLogger("jobs")


def _il_y_a_mois(n: int):
    j = aujourd_hui()
    a, m = ajouter_mois(j.year, j.month, -n)
    jour = min(j.day, 28)
    return j.replace(year=a, month=m, day=jour)


def purger(db) -> None:
    regles = P.tous(db)
    # Comptes sortis : désactivation à la date de sortie, suppression après le délai.
    for u in db.scalars(select(Utilisateur).where(Utilisateur.date_sortie.is_not(None),
                                                  Utilisateur.date_sortie < aujourd_hui(),
                                                  Utilisateur.actif.is_(True))):
        u.actif = False
        db.execute(delete(SessionAuth).where(SessionAuth.utilisateur_id == u.id))
        journaliser(db, None, "desactivation_auto", "utilisateur", u.id, None, {"date_sortie": u.date_sortie.isoformat()})
    limite_comptes = _il_y_a_mois(regles["retention_comptes_sortis_mois"])
    for u in db.scalars(select(Utilisateur).where(Utilisateur.date_sortie.is_not(None),
                                                  Utilisateur.date_sortie < limite_comptes,
                                                  Utilisateur.role != "admin")):
        journaliser(db, None, "purge_compte", "utilisateur", u.id, {"matricule": u.matricule}, None)
        db.query(Utilisateur).filter(Utilisateur.manager_id == u.id).update({"manager_id": None})
        db.execute(delete(Pointage).where(Pointage.utilisateur_id == u.id))
        db.execute(delete(SessionAuth).where(SessionAuth.utilisateur_id == u.id))
        db.delete(u)

    limite = debut_jour_utc(_il_y_a_mois(regles["retention_pointages_mois"]))
    n = db.execute(delete(Pointage).where(Pointage.horodatage < limite)).rowcount
    db.execute(delete(Audit).where(Audit.horodatage < limite))
    db.execute(delete(SessionAuth).where(SessionAuth.expire_le < maintenant_utc()))
    if n:
        log.info("Purge : %s badgeage(s) antérieurs au %s supprimés", n, limite.date())
    db.commit()


def relancer_oublis(db) -> None:
    heures = P.lire(db, "relance_oubli_depart_h")
    if not heures:
        return
    duree_max = timedelta(hours=P.lire(db, "duree_max_poste_h"))
    maintenant = maintenant_utc()
    candidats = db.scalars(select(Pointage).where(
        Pointage.type == "entree", Pointage.relance_envoyee.is_(False),
        Pointage.horodatage < maintenant - timedelta(hours=heures),
        Pointage.horodatage > maintenant - duree_max - timedelta(days=1)))
    for p in candidats:
        suivant = db.scalar(select(Pointage.id).where(
            Pointage.utilisateur_id == p.utilisateur_id, Pointage.horodatage > p.horodatage).limit(1))
        p.relance_envoyee = True
        if suivant is None and p.utilisateur.actif:
            envoyer(p.utilisateur.email, "Badgeage : départ non enregistré",
                    f"Bonjour {p.utilisateur.prenom},\n\nVotre arrivée du {format_date(p.horodatage)} à "
                    f"{format_heure(p.horodatage)} n'est suivie d'aucun départ.\nSi vous avez oublié de badger, "
                    f"utilisez « J'ai oublié de badger » : {get_settings().base_url}/oubli\n\nBadgeage Proximy")
    db.commit()


def rappeler_validations(db) -> None:
    """Un rappel par jour (vers 8 h) aux managers ayant des saisies en attente."""
    if not P.lire(db, "validation_manager"):
        return
    cle = "_dernier_rappel_validations"
    deja = db.get(Parametre, cle)
    if deja and deja.valeur == aujourd_hui().isoformat():
        return
    if datetime.now(tz()).hour < 8:
        return
    attente = db.scalars(select(Pointage).where(Pointage.statut_validation == "en_attente")).all()
    if attente:
        for m in db.scalars(select(Utilisateur).where(Utilisateur.actif.is_(True), Utilisateur.email.is_not(None))):
            equipe = ids_equipe(db, m)
            n = sum(1 for p in attente if p.utilisateur_id in equipe)
            if n:
                envoyer(m.email, f"Badgeage : {n} saisie(s) manuelle(s) à valider",
                        f"Bonjour {m.prenom},\n\n{n} saisie(s) manuelle(s) de votre équipe attendent votre "
                        f"validation : {get_settings().base_url}/validations\n\nBadgeage Proximy")
    if deja:
        deja.valeur = aujourd_hui().isoformat()
    else:
        db.add(Parametre(cle=cle, valeur=aujourd_hui().isoformat()))
    db.commit()


def executer_une_fois() -> None:
    for tache in (purger, relancer_oublis, rappeler_validations):
        with SessionLocal() as db:
            try:
                tache(db)
            except Exception:
                log.exception("Échec de la tâche %s", tache.__name__)
                db.rollback()


def boucle() -> None:
    intervalle = get_settings().jobs_intervalle_minutes * 60
    log.info("Worker démarré (intervalle %s min)", intervalle // 60)
    while True:
        executer_une_fois()
        time.sleep(intervalle)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    boucle()
