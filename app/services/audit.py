from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Audit, Utilisateur

_EXCLUS = {"mot_de_passe_hash", "echecs_connexion", "bloque_jusqu_a", "derniere_connexion"}


def _valeur(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def instantane(obj) -> dict:
    """Copie des colonnes d'un objet, pour le journal d'audit."""
    return {c.key: _valeur(getattr(obj, c.key)) for c in obj.__table__.columns if c.key not in _EXCLUS}


def journaliser(db: Session, acteur: Utilisateur | None, action: str, cible_type: str, cible_id: int | None,
                avant: dict | None, apres: dict | None) -> None:
    db.add(Audit(acteur_id=acteur.id if acteur else None, action=action, cible_type=cible_type,
                 cible_id=cible_id, avant=avant, apres=apres))
