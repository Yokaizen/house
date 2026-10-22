"""Modèle de données.

Principe de minimisation : aucune coordonnée GPS de badgeage n'est stockée.
Pour chaque badgeage on conserve seulement le résultat du contrôle de
périmètre (zone_statut), le type d'appareil et la précision annoncée par
l'appareil (en mètres, ce qui ne permet pas de retrouver une position).
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


# Valeurs autorisées (stockées en texte pour des migrations simples).
ROLES = ("salarie", "manager", "rh", "admin")
ROLE_LIBELLES = {"salarie": "Salarié", "manager": "Manager", "rh": "RH (lecture)", "admin": "Administrateur"}

TYPES_POINTAGE = ("entree", "sortie")
SOURCES = ("badge", "manuel", "correction")
ZONES = ("dans_zone", "hors_zone", "indetermine", "indisponible", "non_applicable")
ZONE_LIBELLES = {
    "dans_zone": "Dans la zone",
    "hors_zone": "Hors zone",
    "indetermine": "Indéterminé",
    "indisponible": "Position refusée",
    "non_applicable": "Sans contrôle",
}
APPAREILS = ("mobile", "ordinateur")
VALIDATIONS = ("valide", "en_attente", "refuse")


class Etablissement(Base):
    __tablename__ = "etablissements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    nom: Mapped[str] = mapped_column(String(120))
    adresse_numero: Mapped[str | None] = mapped_column(String(20))
    adresse_voie: Mapped[str | None] = mapped_column(String(200))
    adresse_complement: Mapped[str | None] = mapped_column(String(200))
    code_postal: Mapped[str | None] = mapped_column(String(10))
    ville: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    rayon_m: Mapped[int] = mapped_column(Integer, default=100)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def localise(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricule: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(120))
    prenom: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="salarie")
    etablissement_id: Mapped[int | None] = mapped_column(ForeignKey("etablissements.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    heures_hebdo: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("35"))

    # Domicile (télétravail). Seules les coordonnées géocodées de l'adresse
    # déclarée sont stockées, jamais celles d'un badgeage.
    adresse_numero: Mapped[str | None] = mapped_column(String(20))
    adresse_voie: Mapped[str | None] = mapped_column(String(200))
    adresse_complement: Mapped[str | None] = mapped_column(String(200))
    code_postal: Mapped[str | None] = mapped_column(String(10))
    ville: Mapped[str | None] = mapped_column(String(120))
    domicile_lat: Mapped[float | None] = mapped_column(Float)
    domicile_lon: Mapped[float | None] = mapped_column(Float)
    domicile_rayon_m: Mapped[int | None] = mapped_column(Integer)
    teletravail_autorise: Mapped[bool] = mapped_column(Boolean, default=True)

    mot_de_passe_hash: Mapped[str | None] = mapped_column(String(255))
    doit_changer_mdp: Mapped[bool] = mapped_column(Boolean, default=True)
    # Blocage du compte pour toutes les adresses (voir TentativeConnexion).
    bloque_jusqu_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    date_sortie: Mapped[date | None] = mapped_column(Date)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    etablissement: Mapped[Etablissement | None] = relationship()
    manager: Mapped["Utilisateur | None"] = relationship(remote_side="Utilisateur.id", foreign_keys=[manager_id])

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom}"

    @property
    def domicile_localise(self) -> bool:
        return self.domicile_lat is not None and self.domicile_lon is not None

    @property
    def est_admin(self) -> bool:
        return self.role == "admin"

    @property
    def vue_globale(self) -> bool:
        return self.role in ("admin", "rh")


class SessionAuth(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vu_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    user_agent: Mapped[str | None] = mapped_column(String(300))

    utilisateur: Mapped[Utilisateur] = relationship()


class TentativeConnexion(Base):
    """Échec de connexion, conservé un jour pour limiter les tentatives
    par adresse IP et par compte (app/security.py)."""
    __tablename__ = "tentatives_connexion"

    id: Mapped[int] = mapped_column(primary_key=True)
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, index=True)
    adresse_ip: Mapped[str] = mapped_column(String(45), index=True)
    # Identifiant saisi, en minuscules : compté même s'il ne correspond à aucun compte.
    identifiant: Mapped[str] = mapped_column(String(200))
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)


class Pointage(Base):
    __tablename__ = "pointages"

    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(10))  # entree | sortie
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(15), default="badge")  # badge | manuel | correction

    # Contrôle de périmètre : résultat uniquement.
    zone_statut: Mapped[str] = mapped_column(String(20), default="non_applicable")
    appareil: Mapped[str | None] = mapped_column(String(15))
    precision_m: Mapped[int | None] = mapped_column(Integer)

    # Saisie manuelle (« j'ai oublié de badger »).
    motif: Mapped[str | None] = mapped_column(Text)
    saisi_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    statut_validation: Mapped[str] = mapped_column(String(15), default="valide")
    valide_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    commentaire_validation: Mapped[str | None] = mapped_column(Text)

    # Traçabilité des corrections (le détail avant/après est dans le journal d'audit).
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    modifie_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    modifie_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    relance_envoyee: Mapped[bool] = mapped_column(Boolean, default=False)

    utilisateur: Mapped[Utilisateur] = relationship(foreign_keys=[utilisateur_id])

    @property
    def est_manuel(self) -> bool:
        return self.source != "badge"


class Audit(Base):
    __tablename__ = "audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant, index=True)
    acteur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(50))
    cible_type: Mapped[str] = mapped_column(String(30))
    cible_id: Mapped[int | None] = mapped_column(Integer)
    avant: Mapped[dict | None] = mapped_column(JSON)
    apres: Mapped[dict | None] = mapped_column(JSON)

    acteur: Mapped[Utilisateur | None] = relationship()


class Parametre(Base):
    __tablename__ = "parametres"

    cle: Mapped[str] = mapped_column(String(60), primary_key=True)
    valeur: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
