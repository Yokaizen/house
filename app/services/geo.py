"""Contrôle de périmètre.

La position reçue du navigateur n'est utilisée qu'en mémoire, le temps du
calcul : seule la conclusion (dans_zone, hors_zone, indetermine, indisponible)
est enregistrée.
"""
import math
from dataclasses import dataclass

RAYON_TERRE_M = 6_371_000


@dataclass(frozen=True)
class Lieu:
    latitude: float
    longitude: float
    rayon_m: int


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique (formule de haversine), en mètres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAYON_TERRE_M * math.asin(math.sqrt(a))


def evaluer_zone(
    latitude: float | None,
    longitude: float | None,
    precision_m: float | None,
    lieux: list[Lieu],
    precision_max_m: float,
) -> str:
    """Renvoie le statut de zone d'un badgeage.

    - indisponible : le navigateur n'a pas fourni de position (refus, erreur) ;
    - indetermine  : position trop imprécise pour conclure, ou aucun lieu de
                     référence configuré pour ce salarié ;
    - dans_zone    : à moins de (rayon + précision annoncée) d'un lieu autorisé ;
    - hors_zone    : sinon.
    """
    if latitude is None or longitude is None:
        return "indisponible"
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return "indisponible"
    if not lieux:
        return "indetermine"

    precision = max(float(precision_m or 0), 0.0)
    ecarts = [distance_m(latitude, longitude, l.latitude, l.longitude) - l.rayon_m for l in lieux]
    plus_proche = min(ecarts)

    if precision > precision_max_m:
        # Même avec une position imprécise, on peut conclure « hors zone »
        # si le cercle d'incertitude ne touche aucun lieu autorisé.
        return "hors_zone" if plus_proche > precision else "indetermine"
    return "dans_zone" if plus_proche <= precision else "hors_zone"
