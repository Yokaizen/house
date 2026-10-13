"""Géocodage d'adresses via l'API Adresse (adresse.data.gouv.fr).

Utilisé uniquement pour les adresses d'établissement et de domicile saisies
par l'administration, jamais pour un badgeage.
"""
import logging
from dataclasses import dataclass

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class Resultat:
    latitude: float
    longitude: float
    libelle: str
    score: float


def adresse_texte(numero: str | None, voie: str | None, code_postal: str | None, ville: str | None) -> str:
    return " ".join(x.strip() for x in (numero, voie, code_postal, ville) if x and x.strip())


def geocoder(adresse: str, code_postal: str | None = None) -> Resultat | None:
    s = get_settings()
    if not s.geocodage_actif or len(adresse.strip()) < 5:
        return None
    params = {"q": adresse, "limit": 1}
    if code_postal:
        params["postcode"] = code_postal.strip()
    try:
        r = httpx.get(s.geocodage_url, params=params, timeout=8)
        r.raise_for_status()
        features = r.json().get("features") or []
    except (httpx.HTTPError, ValueError) as e:
        log.warning("Géocodage impossible : %s", e)
        return None
    if not features:
        return None
    f = features[0]
    lon, lat = f["geometry"]["coordinates"]
    return Resultat(lat, lon, f["properties"].get("label", ""), float(f["properties"].get("score", 0)))
