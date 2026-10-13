"""Logique de badgeage : enregistrement, appariement arrivée/départ,
journées, totaux, comparaison au contrat et alertes."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etablissement, Pointage, Utilisateur
from app.services import parametres as P
from app.services.audit import journaliser, instantane
from app.services.geo import Lieu, evaluer_zone
from app.services.temps import (
    aujourd_hui,
    debut_jour_utc,
    jours_ouvres,
    local_vers_utc,
    maintenant_utc,
    vers_local,
    vers_utc,
)


class ErreurMetier(Exception):
    pass


# ---------------------------------------------------------------------------
# Lieux autorisés et badgeage
# ---------------------------------------------------------------------------

def lieux_autorises(db: Session, u: Utilisateur, regles: dict | None = None) -> list[Lieu]:
    regles = regles or P.tous(db)
    lieux: list[Lieu] = []
    requete = select(Etablissement).where(Etablissement.actif.is_(True))
    if not regles["tous_sites_autorises"]:
        requete = requete.where(Etablissement.id == u.etablissement_id)
    for e in db.scalars(requete):
        if e.localise:
            lieux.append(Lieu(e.latitude, e.longitude, e.rayon_m or regles["rayon_defaut_m"]))
    if u.teletravail_autorise and u.domicile_localise:
        lieux.append(Lieu(u.domicile_lat, u.domicile_lon, u.domicile_rayon_m or regles["rayon_defaut_m"]))
    return lieux


def _pointages_valides(db: Session, utilisateur_id: int, depuis: datetime):
    return db.scalars(
        select(Pointage)
        .where(Pointage.utilisateur_id == utilisateur_id, Pointage.horodatage >= depuis,
               Pointage.statut_validation != "refuse")
        .order_by(Pointage.horodatage)
    ).all()


@dataclass
class EtatBadge:
    prochain: str | None  # "entree", "sortie" ou None si la journée est terminée
    dernier: Pointage | None
    arrivees_du_jour: int
    max_arrivees: int


def etat_courant(db: Session, u: Utilisateur, regles: dict | None = None) -> EtatBadge:
    regles = regles or P.tous(db)
    duree_max = timedelta(hours=regles["duree_max_poste_h"])
    maintenant = maintenant_utc()
    recents = _pointages_valides(db, u.id, debut_jour_utc(aujourd_hui() - timedelta(days=2)))
    dernier = recents[-1] if recents else None

    if dernier and dernier.type == "entree" and maintenant - vers_utc(dernier.horodatage) <= duree_max:
        return EtatBadge("sortie", dernier, 0, regles["paires_max_par_jour"])

    jour = aujourd_hui()
    arrivees = sum(1 for p in recents if p.type == "entree" and vers_local(p.horodatage).date() == jour)
    prochain = "entree" if arrivees < regles["paires_max_par_jour"] else None
    return EtatBadge(prochain, dernier, arrivees, regles["paires_max_par_jour"])


def detecter_appareil(indication: str | None, user_agent: str | None) -> str:
    if indication in ("mobile", "ordinateur"):
        return indication
    ua = (user_agent or "").lower()
    return "mobile" if any(m in ua for m in ("mobi", "android", "iphone", "ipad")) else "ordinateur"


def badger(
    db: Session,
    u: Utilisateur,
    type_attendu: str,
    latitude: float | None,
    longitude: float | None,
    precision_m: float | None,
    appareil: str,
) -> Pointage:
    regles = P.tous(db)
    etat = etat_courant(db, u, regles)
    if etat.prochain is None:
        raise ErreurMetier(
            "Vous avez déjà badgé votre arrivée et votre départ aujourd'hui. "
            "En cas d'erreur, utilisez « J'ai oublié de badger » ou contactez votre manager."
        )
    if type_attendu != etat.prochain:
        raise ErreurMetier("L'état de votre badgeage a changé entre-temps. Rechargez la page.")

    seuil = regles["precision_max_mobile_m"] if appareil == "mobile" else regles["precision_max_ordinateur_m"]
    statut = evaluer_zone(latitude, longitude, precision_m, lieux_autorises(db, u, regles), seuil)
    p = Pointage(
        utilisateur_id=u.id,
        type=type_attendu,
        horodatage=maintenant_utc(),
        source="badge",
        zone_statut=statut,
        appareil=appareil,
        precision_m=round(precision_m) if precision_m is not None and latitude is not None else None,
        statut_validation="valide",
        cree_par_id=u.id,
    )
    db.add(p)
    db.commit()
    return p


# ---------------------------------------------------------------------------
# Saisies manuelles et corrections
# ---------------------------------------------------------------------------

def _controler_type(type_: str) -> None:
    if type_ not in ("entree", "sortie"):
        raise ErreurMetier("Type de badgeage invalide.")


def saisie_manuelle(db: Session, u: Utilisateur, type_: str, jour: date, heure: time, motif: str) -> Pointage:
    """« J'ai oublié de badger » : saisie par le salarié lui-même."""
    _controler_type(type_)
    motif = (motif or "").strip()
    if len(motif) < 3:
        raise ErreurMetier("Le motif est obligatoire.")
    regles = P.tous(db)
    horodatage = local_vers_utc(jour, heure)
    if horodatage > maintenant_utc():
        raise ErreurMetier("Impossible de saisir un badgeage dans le futur.")
    limite = aujourd_hui() - timedelta(days=regles["saisie_manuelle_jours_max"])
    if jour < limite:
        raise ErreurMetier(
            f"La saisie manuelle est limitée aux {regles['saisie_manuelle_jours_max']} derniers jours. "
            "Contactez votre manager pour une date plus ancienne."
        )
    p = Pointage(
        utilisateur_id=u.id,
        type=type_,
        horodatage=horodatage,
        source="manuel",
        zone_statut="non_applicable",
        motif=motif[:1000],
        statut_validation="en_attente" if regles["validation_manager"] else "valide",
        cree_par_id=u.id,
    )
    db.add(p)
    db.flush()
    journaliser(db, u, "saisie_manuelle", "pointage", p.id, None, instantane(p))
    db.commit()
    return p


def ajout_par_responsable(db: Session, acteur: Utilisateur, cible: Utilisateur, type_: str,
                          jour: date, heure: time, motif: str) -> Pointage:
    _controler_type(type_)
    motif = (motif or "").strip()
    if len(motif) < 3:
        raise ErreurMetier("Le motif est obligatoire.")
    horodatage = local_vers_utc(jour, heure)
    if horodatage > maintenant_utc():
        raise ErreurMetier("Impossible de saisir un badgeage dans le futur.")
    p = Pointage(
        utilisateur_id=cible.id, type=type_, horodatage=horodatage, source="correction",
        zone_statut="non_applicable", motif=motif[:1000], statut_validation="valide",
        cree_par_id=acteur.id, valide_par_id=acteur.id, valide_le=maintenant_utc(),
    )
    db.add(p)
    db.flush()
    journaliser(db, acteur, "ajout_pointage", "pointage", p.id, None, instantane(p))
    db.commit()
    return p


def modifier_pointage(db: Session, acteur: Utilisateur, p: Pointage, type_: str, jour: date,
                      heure: time, motif: str) -> None:
    _controler_type(type_)
    motif = (motif or "").strip()
    if len(motif) < 3:
        raise ErreurMetier("Le motif de la correction est obligatoire.")
    horodatage = local_vers_utc(jour, heure)
    if horodatage > maintenant_utc():
        raise ErreurMetier("Impossible de placer un badgeage dans le futur.")
    avant = instantane(p)
    p.type = type_
    p.horodatage = horodatage
    p.modifie_par_id = acteur.id
    p.modifie_le = maintenant_utc()
    p.commentaire_validation = motif[:1000]
    journaliser(db, acteur, "modification_pointage", "pointage", p.id, avant, instantane(p))
    db.commit()


def supprimer_pointage(db: Session, acteur: Utilisateur, p: Pointage, motif: str) -> None:
    motif = (motif or "").strip()
    if len(motif) < 3:
        raise ErreurMetier("Le motif de la suppression est obligatoire.")
    avant = instantane(p)
    avant["motif_suppression"] = motif[:1000]
    journaliser(db, acteur, "suppression_pointage", "pointage", p.id, avant, None)
    db.delete(p)
    db.commit()


def valider_saisie(db: Session, acteur: Utilisateur, p: Pointage, accepter: bool, commentaire: str = "") -> None:
    if p.statut_validation != "en_attente":
        raise ErreurMetier("Cette saisie a déjà été traitée.")
    avant = instantane(p)
    p.statut_validation = "valide" if accepter else "refuse"
    p.valide_par_id = acteur.id
    p.valide_le = maintenant_utc()
    p.commentaire_validation = (commentaire or "").strip()[:1000] or None
    journaliser(db, acteur, "validation_saisie" if accepter else "refus_saisie", "pointage", p.id,
                avant, instantane(p))
    db.commit()


# ---------------------------------------------------------------------------
# Périmètre de visibilité
# ---------------------------------------------------------------------------

def ids_equipe(db: Session, manager: Utilisateur, niveaux: int | None = None) -> set[int]:
    niveaux = niveaux or P.lire(db, "perimetre_manager_niveaux")
    ids: set[int] = set()
    frontiere = {manager.id}
    for _ in range(niveaux):
        if not frontiere:
            break
        suivants = set(db.scalars(select(Utilisateur.id).where(Utilisateur.manager_id.in_(frontiere))))
        suivants -= ids | {manager.id}
        ids |= suivants
        frontiere = suivants
    return ids


def peut_voir(db: Session, acteur: Utilisateur, cible: Utilisateur) -> bool:
    return acteur.vue_globale or acteur.id == cible.id or cible.id in ids_equipe(db, acteur)


def peut_corriger(db: Session, acteur: Utilisateur, cible: Utilisateur) -> bool:
    if acteur.est_admin:
        return True
    if acteur.id == cible.id:
        return False
    return P.lire(db, "manager_peut_corriger") and cible.id in ids_equipe(db, acteur)


def peut_valider(db: Session, acteur: Utilisateur, cible: Utilisateur) -> bool:
    if acteur.est_admin:
        return True
    return acteur.id != cible.id and cible.id in ids_equipe(db, acteur)


# ---------------------------------------------------------------------------
# Postes, journées, synthèses
# ---------------------------------------------------------------------------

ALERTES = {
    "sortie_manquante": "Départ non badgé",
    "entree_manquante": "Arrivée non badgée",
    "duree_jour": "Durée journalière élevée",
    "amplitude": "Amplitude élevée",
    "repos": "Repos insuffisant",
    "hors_zone": "Badgeage hors zone",
    "indetermine": "Zone indéterminée",
    "indisponible": "Position refusée",
    "manuel": "Saisie manuelle",
    "en_attente": "Saisie à valider",
    "duree_semaine": "Durée hebdomadaire élevée",
}
# Alertes signalant un point de vigilance (les autres sont informatives).
ALERTES_GRAVES = {"sortie_manquante", "entree_manquante", "duree_jour", "amplitude", "repos", "hors_zone",
                  "duree_semaine"}


@dataclass
class Poste:
    entree: Pointage | None
    sortie: Pointage | None
    en_cours: bool = False

    @property
    def debut(self) -> datetime | None:
        return vers_utc(self.entree.horodatage) if self.entree else None

    @property
    def fin(self) -> datetime | None:
        return vers_utc(self.sortie.horodatage) if self.sortie else None

    @property
    def duree(self) -> timedelta | None:
        if self.debut and self.fin:
            return self.fin - self.debut
        return None

    @property
    def jour(self) -> date:
        """Un poste de nuit est rattaché au jour de son arrivée."""
        return vers_local(self.debut or self.fin).date()

    @property
    def pointages(self) -> list[Pointage]:
        return [p for p in (self.entree, self.sortie) if p]


def apparier(pointages: list[Pointage], duree_max: timedelta, maintenant: datetime | None = None) -> list[Poste]:
    """Associe chaque arrivée au départ qui la suit (y compris après minuit)."""
    maintenant = maintenant or maintenant_utc()
    postes: list[Poste] = []
    ouvert: Pointage | None = None
    for p in sorted(pointages, key=lambda x: vers_utc(x.horodatage)):
        if p.statut_validation == "refuse":
            continue
        if p.type == "entree":
            if ouvert:
                postes.append(Poste(ouvert, None))
            ouvert = p
        else:
            if ouvert and vers_utc(p.horodatage) - vers_utc(ouvert.horodatage) <= duree_max:
                postes.append(Poste(ouvert, p))
            else:
                if ouvert:
                    postes.append(Poste(ouvert, None))
                postes.append(Poste(None, p))
            ouvert = None
    if ouvert:
        postes.append(Poste(ouvert, None, en_cours=maintenant - vers_utc(ouvert.horodatage) <= duree_max))
    return postes


@dataclass
class Journee:
    jour: date
    postes: list[Poste] = field(default_factory=list)
    alertes: list[str] = field(default_factory=list)
    repos_avant: timedelta | None = None

    @property
    def duree(self) -> timedelta:
        return sum((p.duree for p in self.postes if p.duree), timedelta())

    @property
    def amplitude(self) -> timedelta | None:
        debuts = [p.debut for p in self.postes if p.debut]
        fins = [p.fin for p in self.postes if p.fin]
        if debuts and fins and max(fins) > min(debuts):
            return max(fins) - min(debuts)
        return None

    @property
    def pointages(self) -> list[Pointage]:
        return [x for p in self.postes for x in p.pointages]

    @property
    def alertes_graves(self) -> list[str]:
        return [a for a in self.alertes if a in ALERTES_GRAVES]


def construire_journees(postes: list[Poste], regles: dict) -> dict[date, Journee]:
    journees: dict[date, Journee] = {}
    for poste in postes:
        journees.setdefault(poste.jour, Journee(poste.jour)).postes.append(poste)

    fin_precedente: datetime | None = None
    for jour in sorted(journees):
        j = journees[jour]
        alertes: list[str] = []
        for poste in j.postes:
            if poste.entree and not poste.sortie and not poste.en_cours:
                alertes.append("sortie_manquante")
            if poste.sortie and not poste.entree:
                alertes.append("entree_manquante")
        premier_debut = min((p.debut for p in j.postes if p.debut), default=None)
        if fin_precedente and premier_debut and premier_debut > fin_precedente:
            j.repos_avant = premier_debut - fin_precedente
            if j.repos_avant < timedelta(hours=regles["alerte_repos_quotidien_h"]):
                alertes.append("repos")
        if j.duree > timedelta(hours=regles["alerte_duree_jour_h"]):
            alertes.append("duree_jour")
        if j.amplitude and j.amplitude > timedelta(hours=regles["alerte_amplitude_h"]):
            alertes.append("amplitude")
        for p in j.pointages:
            if p.zone_statut in ("hors_zone", "indetermine", "indisponible"):
                alertes.append(p.zone_statut)
            if p.est_manuel:
                alertes.append("manuel")
            if p.statut_validation == "en_attente":
                alertes.append("en_attente")
        j.alertes = list(dict.fromkeys(alertes))
        fins = [p.fin for p in j.postes if p.fin]
        if fins:
            fin_precedente = max(fins)
    return journees


@dataclass
class Synthese:
    utilisateur: Utilisateur
    debut: date
    fin: date
    journees: dict[date, Journee]
    heures_contrat: Decimal
    regles: dict = field(default_factory=dict)

    @property
    def journees_periode(self) -> list[Journee]:
        return [self.journees[j] for j in sorted(self.journees) if self.debut <= j <= self.fin]

    @property
    def duree(self) -> timedelta:
        return sum((j.duree for j in self.journees_periode), timedelta())

    @property
    def jours_travailles(self) -> int:
        return sum(1 for j in self.journees_periode if j.duree > timedelta())

    @property
    def duree_attendue(self) -> timedelta:
        """Durée théorique : contrat hebdomadaire / 5 par jour ouvré (hors fériés),
        jusqu'à aujourd'hui inclus. Les absences (congés, maladie) ne sont pas connues."""
        fin = min(self.fin, aujourd_hui())
        if fin < self.debut:
            return timedelta()
        par_jour = float(self.heures_contrat) / 5
        return timedelta(hours=par_jour * jours_ouvres(self.debut, fin))

    @property
    def ecart(self) -> timedelta:
        return self.duree - self.duree_attendue

    def compte_alertes(self) -> dict[str, int]:
        c: dict[str, int] = defaultdict(int)
        for j in self.journees_periode:
            for a in j.alertes:
                c[a] += 1
        for s in self.semaines():
            if "duree_semaine" in s["alertes"]:
                c["duree_semaine"] += 1
        return dict(c)

    @property
    def nb_alertes_graves(self) -> int:
        return sum(n for a, n in self.compte_alertes().items() if a in ALERTES_GRAVES)

    def semaines(self) -> list[dict]:
        seuil = timedelta(hours=self.regles["alerte_duree_semaine_h"])
        par_semaine: dict[tuple[int, int], list[Journee]] = defaultdict(list)
        for j in self.journees_periode:
            par_semaine[j.jour.isocalendar()[:2]].append(j)
        resultat = []
        for (annee, num), js in sorted(par_semaine.items()):
            duree = sum((x.duree for x in js), timedelta())
            resultat.append({
                "annee": annee, "numero": num, "duree": duree,
                "contrat": timedelta(hours=float(self.heures_contrat)),
                "alertes": ["duree_semaine"] if duree > seuil else [],
            })
        return resultat

    def par_mois(self) -> dict[tuple[int, int], timedelta]:
        d: dict[tuple[int, int], timedelta] = defaultdict(timedelta)
        for j in self.journees_periode:
            d[(j.jour.year, j.jour.month)] += j.duree
        return dict(d)


def syntheses(db: Session, utilisateurs: list[Utilisateur], debut: date, fin: date) -> list[Synthese]:
    """Calcule les journées de chaque utilisateur sur [debut, fin] (dates locales)."""
    if not utilisateurs:
        return []
    regles = P.tous(db)
    duree_max = timedelta(hours=regles["duree_max_poste_h"])
    # Marge d'un jour avant (poste de nuit, repos) et après (départ le lendemain).
    borne_inf = debut_jour_utc(debut - timedelta(days=1))
    borne_sup = debut_jour_utc(fin + timedelta(days=2))
    ids = [u.id for u in utilisateurs]
    par_utilisateur: dict[int, list[Pointage]] = defaultdict(list)
    for i in range(0, len(ids), 500):
        for p in db.scalars(
            select(Pointage).where(Pointage.utilisateur_id.in_(ids[i:i + 500]),
                                   Pointage.horodatage >= borne_inf, Pointage.horodatage < borne_sup)
        ):
            par_utilisateur[p.utilisateur_id].append(p)

    resultat = []
    for u in utilisateurs:
        postes = apparier(par_utilisateur[u.id], duree_max)
        resultat.append(Synthese(u, debut, fin, construire_journees(postes, regles),
                                 u.heures_hebdo or Decimal("35"), regles))
    return resultat


def journees_en_liste(s: Synthese) -> list[tuple[date, Journee | None]]:
    """Tous les jours de la période, travaillés ou non, du plus récent au plus ancien."""
    jours = []
    j = min(s.fin, aujourd_hui())
    while j >= s.debut:
        jours.append((j, s.journees.get(j)))
        j -= timedelta(days=1)
    return jours
