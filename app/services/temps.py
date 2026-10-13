"""Fuseau horaire, jours fériés et formatage des durées."""
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.config import get_settings

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def maintenant_utc() -> datetime:
    return datetime.now(timezone.utc)


def aujourd_hui() -> date:
    return datetime.now(tz()).date()


def vers_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:  # SQLite renvoie des dates naïves (stockées en UTC)
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz())


def vers_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def local_vers_utc(jour: date, heure: time) -> datetime:
    return datetime.combine(jour, heure, tzinfo=tz()).astimezone(timezone.utc)


def debut_jour_utc(jour: date) -> datetime:
    return local_vers_utc(jour, time(0, 0))


@lru_cache(maxsize=64)
def paques(annee: int) -> date:
    """Dimanche de Pâques (algorithme de Meeus/Jones/Butcher)."""
    a = annee % 19
    b, c = divmod(annee, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = (h + l - 7 * m + 114) % 31 + 1
    return date(annee, mois, jour)


@lru_cache(maxsize=64)
def jours_feries(annee: int) -> frozenset[date]:
    p = paques(annee)
    return frozenset({
        date(annee, 1, 1), p + timedelta(days=1), date(annee, 5, 1), date(annee, 5, 8),
        p + timedelta(days=39), p + timedelta(days=50), date(annee, 7, 14), date(annee, 8, 15),
        date(annee, 11, 1), date(annee, 11, 11), date(annee, 12, 25),
    })


def est_jour_ouvre(jour: date) -> bool:
    return jour.weekday() < 5 and jour not in jours_feries(jour.year)


def jours_ouvres(debut: date, fin: date) -> int:
    n, j = 0, debut
    while j <= fin:
        if est_jour_ouvre(j):
            n += 1
        j += timedelta(days=1)
    return n


def format_duree(td: timedelta | float | None, signe: bool = False) -> str:
    """Durée au format « 7 h 05 » (heures décimales acceptées)."""
    if td is None:
        return "–"
    minutes = round((td.total_seconds() / 60) if isinstance(td, timedelta) else td * 60)
    prefixe = ""
    if minutes < 0:
        prefixe, minutes = "−", -minutes
    elif signe and minutes > 0:
        prefixe = "+"
    h, m = divmod(minutes, 60)
    return f"{prefixe}{h} h {m:02d}"


def format_heure(dt: datetime | None) -> str:
    return vers_local(dt).strftime("%H:%M") if dt else "–"


def format_date(j: date | datetime | None, avec_jour: bool = False) -> str:
    if j is None:
        return "–"
    if isinstance(j, datetime):
        j = vers_local(j).date()
    s = j.strftime("%d/%m/%Y")
    return f"{JOURS[j.weekday()][:3]}. {s}" if avec_jour else s


def libelle_mois(annee: int, mois: int) -> str:
    return f"{MOIS[mois - 1]} {annee}"


def fin_de_mois(annee: int, mois: int) -> date:
    if mois == 12:
        return date(annee, 12, 31)
    return date(annee, mois + 1, 1) - timedelta(days=1)


def ajouter_mois(annee: int, mois: int, delta: int) -> tuple[int, int]:
    total = annee * 12 + (mois - 1) + delta
    return total // 12, total % 12 + 1
