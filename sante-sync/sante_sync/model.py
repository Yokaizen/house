"""Format commun des fichiers produits, conversions d'unités, agrégation par jour.

Heures : on garde l'heure « murale » telle qu'enregistrée par l'appareil
(l'heure locale du lieu où vous étiez), sans le décalage horaire.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .store import Table

# ---------------------------------------------------------------- schémas

DAILY_FILE = "apple_quotidien.csv"
WORKOUT_FILE = "apple_activites.csv"
WEIGHT_FILE = "apple_pesees.csv"

DAILY_COLUMNS = [
    "date",
    "pas", "distance_km", "etages", "calories_actives_kcal", "calories_repos_kcal",
    "minutes_exercice", "heures_debout",
    "fc_repos_bpm", "fc_moyenne_bpm", "fc_min_bpm", "fc_max_bpm", "fc_marche_bpm",
    "vfc_sdnn_ms", "frequence_respiratoire", "spo2_pct", "vo2max",
    "sommeil_total_h", "sommeil_leger_h", "sommeil_profond_h", "sommeil_paradoxal_h",
    "eveil_nuit_h", "au_lit_h", "coucher", "lever",
    "nb_activites", "minutes_activites", "activites",
    "origine",
]
DAILY_DECIMALS = {
    "pas": 0, "distance_km": 2, "etages": 0, "calories_actives_kcal": 0, "calories_repos_kcal": 0,
    "minutes_exercice": 0, "heures_debout": 0, "fc_repos_bpm": 1, "fc_moyenne_bpm": 1,
    "fc_min_bpm": 0, "fc_max_bpm": 0, "fc_marche_bpm": 1, "vfc_sdnn_ms": 1,
    "frequence_respiratoire": 1, "spo2_pct": 1, "vo2max": 1,
    "sommeil_total_h": 2, "sommeil_leger_h": 2, "sommeil_profond_h": 2, "sommeil_paradoxal_h": 2,
    "eveil_nuit_h": 2, "au_lit_h": 2, "minutes_activites": 0,
}

WORKOUT_COLUMNS = [
    "id", "date", "debut", "fin", "type", "duree_min", "distance_km", "calories_kcal",
    "fc_moyenne_bpm", "fc_max_bpm", "source", "id_service", "origine",
]
WORKOUT_DECIMALS = {"duree_min": 1, "distance_km": 2, "calories_kcal": 0, "fc_moyenne_bpm": 0, "fc_max_bpm": 0}

WEIGHT_COLUMNS = [
    "id", "date", "heure", "poids_kg", "masse_grasse_pct", "masse_maigre_kg", "imc",
    "granularite", "source", "origine",
]
WEIGHT_DECIMALS = {"poids_kg": 2, "masse_grasse_pct": 1, "masse_maigre_kg": 2, "imc": 1}


def open_tables(data_dir: Path) -> dict[str, Table]:
    return {
        "daily": Table(data_dir / DAILY_FILE, "date", DAILY_COLUMNS, DAILY_DECIMALS),
        "workouts": Table(data_dir / WORKOUT_FILE, "id", WORKOUT_COLUMNS, WORKOUT_DECIMALS),
        "weights": Table(data_dir / WEIGHT_FILE, "id", WEIGHT_COLUMNS, WEIGHT_DECIMALS),
    }


# ---------------------------------------------------------------- dates

_TS = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?$")


def parse_ts(s) -> datetime | None:
    """« 2024-02-06 14:30:00 -0800 » → datetime naïf à l'heure murale."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(s)
    s = str(s).strip()
    if not s:
        return None
    m = _TS.match(s)
    if m:
        hms = m.group(2) if m.group(2).count(":") == 2 else m.group(2) + ":00"
        return datetime.strptime(f"{m.group(1)} {hms}", "%Y-%m-%d %H:%M:%S")
    for fmt_ in ("%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt_)
        except ValueError:
            pass
    return None


def night_of(end: datetime) -> date:
    """Nuit rattachée au jour du réveil : un sommeil qui se termine avant 18 h
    compte pour ce jour-là, après 18 h pour le lendemain."""
    return end.date() if end.hour < 18 else end.date() + timedelta(days=1)


def ts_key(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


# ---------------------------------------------------------------- unités

def to_kcal(v: float, unit: str | None) -> float:
    u = (unit or "kcal").lower()
    if u in ("kj",):
        return v / 4.184
    if u in ("cal",) and v > 50000:  # petites calories
        return v / 1000
    return v


def to_km(v: float, unit: str | None) -> float:
    u = (unit or "km").lower()
    return {"km": v, "m": v / 1000, "mi": v * 1.609344, "yd": v * 0.0009144, "ft": v * 0.0003048,
            "cm": v / 100000}.get(u, v)


def to_kg(v: float, unit: str | None) -> float:
    u = (unit or "kg").lower()
    return {"kg": v, "lb": v * 0.45359237, "lbs": v * 0.45359237, "g": v / 1000, "st": v * 6.35029318}.get(u, v)


def to_minutes(v: float, unit: str | None) -> float:
    u = (unit or "min").lower()
    return {"min": v, "s": v / 60, "sec": v / 60, "hr": v * 60, "h": v * 60}.get(u, v)


def to_hours(v: float, unit: str | None) -> float:
    u = (unit or "hr").lower()
    return {"hr": v, "h": v, "min": v / 60, "s": v / 3600}.get(u, v)


def to_pct(v: float, unit: str | None) -> float:
    # Apple stocke 0.97 ; certains exports écrivent 97.
    return v * 100 if v <= 1.0 else v


# ---------------------------------------------------------------- agrégation

# Champs cumulatifs (somme sur la journée) et moyennés.
CUMULATIVE = {"pas", "distance_km", "etages", "calories_actives_kcal", "calories_repos_kcal",
              "minutes_exercice", "heures_debout"}
MEAN = {"fc_repos_bpm", "fc_moyenne_bpm", "fc_marche_bpm", "vfc_sdnn_ms", "frequence_respiratoire", "spo2_pct"}
LAST = {"vo2max"}

SLEEP_STAGES = {"core": "sommeil_leger_h", "deep": "sommeil_profond_h", "rem": "sommeil_paradoxal_h"}


def _pair():
    return [0.0, 0]


def _floatdict():
    return defaultdict(float)


class DayAggregator:
    """Accumule des échantillons et produit une ligne par jour.

    Sources multiples (montre + iPhone qui comptent tous deux les pas) : on ne
    les additionne pas, ce serait compter deux fois. On garde, jour par jour,
    la source au total le plus élevé, sauf si les données sont déjà résumées
    (``presummed``) : la somme est alors juste.
    """

    def __init__(self):
        self.sums = defaultdict(float)               # (day, field, source) -> total
        self.presummed = defaultdict(float)          # (day, field) -> total
        self.means = defaultdict(_pair)   # (day, field) -> [somme, n]
        self.mins: dict = {}
        self.maxs: dict = {}
        self.last: dict = {}                         # (day, field) -> (ts, v)
        self.sleep = defaultdict(_floatdict)  # (night, source) -> stage -> h
        self.sleep_bounds: dict = {}                 # (night, source) -> [start, end]
        self.inbed = defaultdict(float)              # (night, source) -> h
        self.sleep_summ: dict = {}                   # night -> dict déjà calculé

    # -- quantités
    def add(self, field: str, day: date, value: float, source: str = "", presummed: bool = False,
            ts: datetime | None = None):
        if value is None:
            return
        if field in CUMULATIVE:
            if presummed:
                self.presummed[(day, field)] += value
            else:
                self.sums[(day, field, source or "?")] += value
        elif field in MEAN:
            m = self.means[(day, field)]
            m[0] += value
            m[1] += 1
        elif field in LAST:
            t = ts or datetime.combine(day, datetime.min.time())
            if (day, field) not in self.last or t >= self.last[(day, field)][0]:
                self.last[(day, field)] = (t, value)
        elif field == "fc_min_bpm":
            self.mins[(day, field)] = min(value, self.mins.get((day, field), value))
        elif field == "fc_max_bpm":
            self.maxs[(day, field)] = max(value, self.maxs.get((day, field), value))

    # -- sommeil segment par segment
    def add_sleep_segment(self, start: datetime, end: datetime, stage: str, source: str = ""):
        if not start or not end or end <= start:
            return
        hours = (end - start).total_seconds() / 3600
        night = night_of(end)
        key = (night, source or "?")
        st = stage.lower()
        if st in ("inbed", "in bed", "au lit"):
            self.inbed[key] += hours
            return
        if st in ("awake", "éveil", "eveil"):
            self.sleep[key]["awake"] += hours
            return
        if st in ("core", "deep", "rem"):
            self.sleep[key][st] += hours
        else:  # Asleep / Unspecified
            self.sleep[key]["unspecified"] += hours
        b = self.sleep_bounds.get(key)
        if b is None:
            self.sleep_bounds[key] = [start, end]
        else:
            b[0] = min(b[0], start)
            b[1] = max(b[1], end)

    # -- sommeil déjà résumé par l'app
    def add_sleep_summary(self, night: date, values: dict):
        self.sleep_summ[night] = values

    def result(self) -> dict[date, dict]:
        out: dict[date, dict] = defaultdict(dict)
        best = {}
        for (day, field, source), v in self.sums.items():
            if v > best.get((day, field), -1):
                best[(day, field)] = v
        for (day, field), v in best.items():
            out[day][field] = v
        for (day, field), v in self.presummed.items():  # déjà dédupliqué par l'app : prioritaire
            out[day][field] = v
        for (day, field), (s, n) in self.means.items():
            if n:
                out[day][field] = s / n
        for (day, field), v in self.mins.items():
            out[day][field] = v
        for (day, field), v in self.maxs.items():
            out[day][field] = v
        for (day, field), (_, v) in self.last.items():
            out[day][field] = v

        # sommeil : par nuit, la source au plus long sommeil
        nights = defaultdict(list)
        for (night, source), stages in self.sleep.items():
            asleep = sum(h for s, h in stages.items() if s != "awake")
            nights[night].append((asleep, source))
        for night, cands in nights.items():
            asleep, source = max(cands)
            stages = self.sleep[(night, source)]
            row = out[night]
            if asleep > 0:
                row["sommeil_total_h"] = asleep
            has_stages = any(stages.get(s, 0) > 0 for s in SLEEP_STAGES)
            if has_stages:  # la montre mesure les phases : une phase absente vaut vraiment 0
                for s, col in SLEEP_STAGES.items():
                    row[col] = stages.get(s, 0.0)
            if "awake" in stages:
                row["eveil_nuit_h"] = stages["awake"]
            b = self.sleep_bounds.get((night, source))
            if b:
                row["coucher"] = b[0].strftime("%Y-%m-%d %H:%M")
                row["lever"] = b[1].strftime("%Y-%m-%d %H:%M")
        for (night, source), h in self.inbed.items():
            if h > out[night].get("au_lit_h", 0):
                out[night]["au_lit_h"] = h
        for night, values in self.sleep_summ.items():
            out[night].update({k: v for k, v in values.items() if v is not None})
        return dict(out)


def workout_id(start: datetime) -> str:
    """Clé d'une activité : son heure de début à la seconde (commune à tous les
    formats d'export, ce qui évite les doublons entre l'app et l'export Apple)."""
    return "act-" + ts_key(start)


def weight_id(ts: datetime) -> str:
    return "pes-" + ts_key(ts)


def short_hash(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]
