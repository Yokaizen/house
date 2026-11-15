"""Lecture des fichiers produits par l'application iPhone Health Auto Export.

Format JSON (version 2, documentation de l'éditeur) :
    {"data": {"metrics": [{"name": "step_count", "units": "count",
                           "data": [{"date": "2024-02-06 14:30:00 -0800", "qty": 8500,
                                     "source": "Apple Watch"}]}],
              "workouts": [{"id": "...", "name": "...", "start": "...", "end": "...",
                            "duration": 1800, "activeEnergyBurned": {"qty": 300, "units": "kcal"}}]}}
Le format CSV (toujours résumé) est lu au mieux, par reconnaissance des en-têtes.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from . import model as m


@dataclass
class Batch:
    """Ce qu'un fichier apporte, déjà au format commun."""
    daily: dict[date, dict] = field(default_factory=dict)
    workouts: list[dict] = field(default_factory=list)
    weights: list[dict] = field(default_factory=list)
    ignored: set = field(default_factory=set)   # mesures reçues mais non reconnues

    def dates(self) -> set[date]:
        ds = set(self.daily)
        ds |= {date.fromisoformat(w["date"]) for w in self.workouts}
        ds |= {date.fromisoformat(w["date"]) for w in self.weights}
        return ds


# nom HAE -> (champ commun, conversion)
METRICS = {
    "step_count": ("pas", None),
    "walking_running_distance": ("distance_km", m.to_km),
    "flights_climbed": ("etages", None),
    "active_energy": ("calories_actives_kcal", m.to_kcal),
    "basal_energy_burned": ("calories_repos_kcal", m.to_kcal),
    "resting_energy": ("calories_repos_kcal", m.to_kcal),
    "apple_exercise_time": ("minutes_exercice", m.to_minutes),
    "apple_stand_hour": ("heures_debout", None),
    "resting_heart_rate": ("fc_repos_bpm", None),
    "walking_heart_rate_average": ("fc_marche_bpm", None),
    "heart_rate_variability": ("vfc_sdnn_ms", None),
    "heart_rate_variability_sdnn": ("vfc_sdnn_ms", None),
    "respiratory_rate": ("frequence_respiratoire", None),
    "blood_oxygen_saturation": ("spo2_pct", m.to_pct),
    "oxygen_saturation": ("spo2_pct", m.to_pct),
    "vo2_max": ("vo2max", None),
}
BODY = {
    "weight_body_mass": ("poids_kg", m.to_kg),
    "body_mass": ("poids_kg", m.to_kg),
    "body_fat_percentage": ("masse_grasse_pct", m.to_pct),
    "lean_body_mass": ("masse_maigre_kg", m.to_kg),
    "body_mass_index": ("imc", None),
}


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, dict):
        return _num(v.get("qty"))
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _qty_unit(obj, default_unit=None):
    if isinstance(obj, dict):
        return _num(obj.get("qty")), obj.get("units", default_unit)
    return _num(obj), default_unit


def _is_presummed(points: list[dict]) -> bool:
    """Données déjà résumées par l'app (option « Summarize Data ») : sources
    fusionnées (« Montre|iPhone ») ou horodatages tous ronds à l'heure."""
    if not points:
        return False
    if any("|" in str(p.get("source", "")) for p in points):
        return True
    for p in points:
        t = m.parse_ts(p.get("date"))
        if t is None or t.minute or t.second:
            return False
    return True


def parse_json_obj(obj: dict) -> Batch:
    data = obj.get("data", obj) if isinstance(obj, dict) else {}
    agg = m.DayAggregator()
    batch = Batch()
    body_rows: dict[str, dict] = {}

    for metric in data.get("metrics", []) or []:
        name = str(metric.get("name", "")).lower()
        units = metric.get("units")
        points = metric.get("data", []) or []
        if name == "sleep_analysis":
            _parse_sleep(points, agg, units)
            continue
        if name == "heart_rate":
            for p in points:
                t = m.parse_ts(p.get("date"))
                if not t:
                    continue
                d = t.date()
                avg = _num(p.get("Avg", p.get("avg", p.get("qty"))))
                mn = _num(p.get("Min", p.get("min")))
                mx = _num(p.get("Max", p.get("max")))
                if avg is not None:
                    agg.add("fc_moyenne_bpm", d, avg)
                agg.add("fc_min_bpm", d, mn if mn is not None else avg)
                agg.add("fc_max_bpm", d, mx if mx is not None else avg)
            continue
        if name in BODY:
            col, conv = BODY[name]
            presum = _is_presummed(points)
            for p in points:
                t = m.parse_ts(p.get("date"))
                v = _num(p.get("qty"))
                if not t or v is None:
                    continue
                if conv:
                    v = conv(v, units)
                key = m.weight_id(t)
                row = body_rows.setdefault(key, {
                    "id": key, "date": t.date().isoformat(), "heure": t.strftime("%H:%M:%S"),
                    "granularite": "moyenne_jour" if presum else "mesure",
                    "source": p.get("source", ""), "origine": "hae"})
                row[col] = v
            continue
        if name not in METRICS:
            if points:
                batch.ignored.add(name)
            continue
        col, conv = METRICS[name]
        presum = _is_presummed(points)
        for p in points:
            t = m.parse_ts(p.get("date"))
            v = _num(p.get("qty"))
            if not t or v is None:
                continue
            if conv:
                v = conv(v, units)
            agg.add(col, t.date(), v, source=str(p.get("source", "")), presummed=presum, ts=t)

    for w in data.get("workouts", []) or []:
        row = _parse_workout(w)
        if row:
            batch.workouts.append(row)

    batch.daily = agg.result()
    for d in batch.daily.values():
        d["origine"] = "hae"
    batch.weights = list(body_rows.values())
    return batch


def _parse_sleep(points, agg: m.DayAggregator, units):
    for p in points:
        if "totalSleep" in p or "core" in p or "asleep" in p and "value" not in p:
            end = m.parse_ts(p.get("sleepEnd")) or m.parse_ts(p.get("inBedEnd"))
            day = m.parse_ts(p.get("date"))
            if day is None and end is None:
                continue
            night = day.date() if day else m.night_of(end)
            h = lambda k: m.to_hours(_num(p.get(k)), units) if _num(p.get(k)) is not None else None
            core, deep, rem, asleep = h("core"), h("deep"), h("rem"), h("asleep")
            total = h("totalSleep")
            if total is None:
                parts = [x for x in (core, deep, rem, asleep) if x is not None]
                total = sum(parts) if parts else None
            vals = {"sommeil_total_h": total if total else None, "au_lit_h": h("inBed") or None,
                    "eveil_nuit_h": h("awake")}
            if any((x or 0) > 0 for x in (core, deep, rem)):
                vals.update({"sommeil_leger_h": core or 0.0, "sommeil_profond_h": deep or 0.0,
                             "sommeil_paradoxal_h": rem or 0.0})
            s_start, s_end = m.parse_ts(p.get("sleepStart")), m.parse_ts(p.get("sleepEnd"))
            if s_start and s_end:
                vals["coucher"] = s_start.strftime("%Y-%m-%d %H:%M")
                vals["lever"] = s_end.strftime("%Y-%m-%d %H:%M")
            agg.add_sleep_summary(night, vals)
        else:
            start = m.parse_ts(p.get("startDate") or p.get("start"))
            end = m.parse_ts(p.get("endDate") or p.get("end"))
            agg.add_sleep_segment(start, end, str(p.get("value", "asleep")), str(p.get("source", "")))


def _parse_workout(w: dict) -> dict | None:
    start = m.parse_ts(w.get("start"))
    end = m.parse_ts(w.get("end"))
    if not start:
        return None
    dur = _num(w.get("duration"))
    duree_min = dur / 60 if dur is not None else ((end - start).total_seconds() / 60 if end else None)
    kcal, ku = _qty_unit(w.get("activeEnergyBurned") or w.get("activeEnergy") or w.get("totalEnergy"), "kcal")
    if isinstance(w.get("activeEnergy"), list):  # série temporelle (v2)
        kcal = None
    dist, du = _qty_unit(w.get("distance"), "km")
    hr = w.get("heartRate") if isinstance(w.get("heartRate"), dict) else {}
    avg = _num(w.get("avgHeartRate")) or _num(hr.get("avg"))
    mx = _num(w.get("maxHeartRate")) or _num(hr.get("max"))
    return {
        "id": m.workout_id(start), "date": start.date().isoformat(),
        "debut": start.strftime("%Y-%m-%d %H:%M:%S"), "fin": end.strftime("%Y-%m-%d %H:%M:%S") if end else None,
        "type": w.get("name") or "Activité", "duree_min": duree_min,
        "distance_km": m.to_km(dist, du) if dist is not None else None,
        "calories_kcal": m.to_kcal(kcal, ku) if kcal is not None else None,
        "fc_moyenne_bpm": avg, "fc_max_bpm": mx, "source": w.get("source", ""),
        "id_service": w.get("id", ""), "origine": "hae",
    }


# ------------------------------------------------------------------ CSV

_CSV_MAP = [  # (motif d'en-tête, champ, conversion depuis l'unité entre parenthèses)
    (r"^step count", "pas", None),
    (r"^walking \+ running distance|^walking running distance", "distance_km", m.to_km),
    (r"^flights climbed", "etages", None),
    (r"^active energy", "calories_actives_kcal", m.to_kcal),
    (r"^(resting|basal) energy", "calories_repos_kcal", m.to_kcal),
    (r"^apple exercise time|^exercise time", "minutes_exercice", m.to_minutes),
    (r"^apple stand hour|^stand hours?", "heures_debout", None),
    (r"^resting heart rate", "fc_repos_bpm", None),
    (r"^walking heart rate", "fc_marche_bpm", None),
    (r"^heart rate variability", "vfc_sdnn_ms", None),
    (r"^respiratory rate", "frequence_respiratoire", None),
    (r"^(blood )?oxygen saturation", "spo2_pct", m.to_pct),
    (r"^vo2 ?max", "vo2max", None),
    (r"^heart rate \[min\]", "fc_min_bpm", None),
    (r"^heart rate \[max\]", "fc_max_bpm", None),
    (r"^heart rate \[avg\]", "fc_moyenne_bpm", None),
    (r"^sleep analysis \[(total|asleep)\]", "sommeil_total_h", m.to_hours),
    (r"^sleep analysis \[core\]", "sommeil_leger_h", m.to_hours),
    (r"^sleep analysis \[deep\]", "sommeil_profond_h", m.to_hours),
    (r"^sleep analysis \[rem\]", "sommeil_paradoxal_h", m.to_hours),
    (r"^sleep analysis \[awake\]", "eveil_nuit_h", m.to_hours),
    (r"^sleep analysis \[in bed\]", "au_lit_h", m.to_hours),
]
_CSV_BODY = [
    (r"^(weight|body mass)( &| \(|$)", "poids_kg", m.to_kg),
    (r"^body fat percentage", "masse_grasse_pct", m.to_pct),
    (r"^lean body mass", "masse_maigre_kg", m.to_kg),
    (r"^body mass index", "imc", None),
]


def parse_csv_text(text: str) -> Batch:
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    date_col = next((h for h in headers if h.lower().startswith(("date", "start"))), None)
    if not date_col:
        raise ValueError("CSV sans colonne de date reconnaissable")
    mapping, body = {}, {}
    for h in headers:
        hl = h.lower().strip()
        unit = (re.search(r"\(([^)]+)\)\s*$", h) or [None, None])[1]
        for pat, col, conv in _CSV_MAP:
            if re.search(pat, hl):
                mapping[h] = (col, conv, unit)
                break
        for pat, col, conv in _CSV_BODY:
            if re.search(pat, hl):
                body[h] = (col, conv, unit)
                break
    batch = Batch()
    for row in reader:
        t = m.parse_ts(row.get(date_col))
        if not t:
            continue
        d = t.date()
        day = batch.daily.setdefault(d, {"origine": "hae"})
        for h, (col, conv, unit) in mapping.items():
            v = _num(row.get(h))
            if v is None:
                continue
            day[col] = conv(v, unit) if conv else v
        brow = {}
        for h, (col, conv, unit) in body.items():
            v = _num(row.get(h))
            if v is not None:
                brow[col] = conv(v, unit) if conv else v
        if brow.get("poids_kg") is not None:
            brow.update({"id": m.weight_id(t), "date": d.isoformat(), "heure": t.strftime("%H:%M:%S"),
                         "granularite": "moyenne_jour" if t.hour == t.minute == 0 else "mesure",
                         "source": "Health Auto Export (CSV)", "origine": "hae"})
            batch.weights.append(brow)
    batch.daily = {d: v for d, v in batch.daily.items() if len(v) > 1}
    return batch


def parse_file(path: Path) -> Batch:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return parse_json_obj(json.loads(text))
    return parse_csv_text(text)


def looks_like_hae_json(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(4096).decode("utf-8", "ignore")
    except OSError:
        return False
    return '"metrics"' in head or '"workouts"' in head or '"data"' in head
