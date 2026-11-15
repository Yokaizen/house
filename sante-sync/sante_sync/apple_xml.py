"""Lecture de l'export complet officiel d'Apple Santé (export.zip / export.xml).

Sur l'iPhone : Santé → photo de profil → Exporter toutes les données de santé.
Le fichier peut peser plusieurs centaines de Mo : lecture en flux, avec point
de reprise régulier pour pouvoir reprendre après une interruption.

Apple ne publie pas sa règle de dédoublonnage entre montre et iPhone ; on
garde, par jour et par mesure cumulative, la source au total le plus élevé
(voir model.DayAggregator). Ces jours-là sont marqués origine=export_apple et
ne remplacent jamais une valeur venue de Health Auto Export.
"""
from __future__ import annotations

import json
import pickle
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import iterparse

from . import model as m
from .hae import Batch

Q = "HKQuantityTypeIdentifier"
QUANTITY = {
    Q + "StepCount": ("pas", None),
    Q + "DistanceWalkingRunning": ("distance_km", m.to_km),
    Q + "FlightsClimbed": ("etages", None),
    Q + "ActiveEnergyBurned": ("calories_actives_kcal", m.to_kcal),
    Q + "BasalEnergyBurned": ("calories_repos_kcal", m.to_kcal),
    Q + "AppleExerciseTime": ("minutes_exercice", m.to_minutes),
    Q + "RestingHeartRate": ("fc_repos_bpm", None),
    Q + "WalkingHeartRateAverage": ("fc_marche_bpm", None),
    Q + "HeartRateVariabilitySDNN": ("vfc_sdnn_ms", None),
    Q + "RespiratoryRate": ("frequence_respiratoire", None),
    Q + "OxygenSaturation": ("spo2_pct", m.to_pct),
    Q + "VO2Max": ("vo2max", None),
}
BODY = {
    Q + "BodyMass": ("poids_kg", m.to_kg),
    Q + "BodyFatPercentage": ("masse_grasse_pct", m.to_pct),
    Q + "LeanBodyMass": ("masse_maigre_kg", m.to_kg),
    Q + "BodyMassIndex": ("imc", None),
}
SLEEP = "HKCategoryTypeIdentifierSleepAnalysis"
STAND = "HKCategoryTypeIdentifierAppleStandHour"
SLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisInBed": "inbed",
    "HKCategoryValueSleepAnalysisAsleep": "asleep",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "asleep",
    "HKCategoryValueSleepAnalysisAsleepCore": "core",
    "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
    "HKCategoryValueSleepAnalysisAsleepREM": "rem",
    "HKCategoryValueSleepAnalysisAwake": "awake",
}
WORKOUT_FR = {
    "Running": "Course à pied", "Walking": "Marche", "Cycling": "Vélo", "Swimming": "Natation",
    "Hiking": "Randonnée", "Yoga": "Yoga", "TraditionalStrengthTraining": "Renforcement musculaire",
    "FunctionalStrengthTraining": "Renforcement fonctionnel", "HighIntensityIntervalTraining": "HIIT",
    "Elliptical": "Elliptique", "Rowing": "Rameur", "Tennis": "Tennis", "Golf": "Golf",
    "CrossTraining": "Entraînement croisé", "Pilates": "Pilates", "Dance": "Danse",
    "CoreTraining": "Gainage", "Cooldown": "Récupération", "Other": "Autre",
}

CHECKPOINT_EVERY = 200_000


@contextmanager
def open_export(path: Path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            # « export.xml » (ou « exportation.xml » selon la langue de l'iPhone) ; à défaut, le plus gros .xml
            xmls = [i for i in z.infolist() if i.filename.lower().endswith(".xml") and "cda" not in i.filename.lower()]
            pref = [i for i in xmls if i.filename.lower().endswith(("export.xml", "exportation.xml"))]
            pick = (pref or sorted(xmls, key=lambda i: i.file_size, reverse=True) or [None])[0]
            name = pick.filename if pick else None
            if not name:
                raise ValueError("export.xml introuvable dans l'archive")
            with z.open(name) as f:
                yield f
    else:
        with path.open("rb") as f:
            yield f


def is_apple_export(path: Path) -> bool:
    p = Path(path)
    if p.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(p) as z:
                return any(n.lower().endswith(".xml") and "apple_health_export" in n.lower() or
                           n.lower().endswith(("export.xml", "exportation.xml")) for n in z.namelist())
        except zipfile.BadZipFile:
            return False
    if p.suffix.lower() == ".xml":
        with p.open("rb") as f:
            return b"HealthData" in f.read(65536)
    return False


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_export(path: Path, checkpoint: Path | None = None, progress=None) -> Batch:
    """Analyse l'export. Si ``checkpoint`` est fourni, l'état est sauvegardé
    régulièrement et une analyse interrompue reprend où elle s'est arrêtée."""
    state = None
    if checkpoint and checkpoint.exists():
        try:
            state = pickle.loads(checkpoint.read_bytes())
        except Exception:
            state = None
    if state:
        agg, body, workouts, done = state["agg"], state["body"], state["workouts"], state["done"]
    else:
        agg, body, workouts, done = m.DayAggregator(), {}, [], 0

    def save_state(n):
        if checkpoint:
            tmp = checkpoint.with_suffix(".tmp")
            tmp.write_bytes(pickle.dumps({"agg": agg, "body": body, "workouts": workouts, "done": n}))
            tmp.replace(checkpoint)

    n = 0
    with open_export(path) as f:
        root = None
        for event, el in iterparse(f, events=("start", "end")):
            if event == "start":
                if root is None:
                    root = el
                continue
            tag = el.tag
            if tag not in ("Record", "Workout", "ActivitySummary"):
                continue
            if tag == "ActivitySummary":
                root.clear()
                continue
            n += 1
            if n <= done:  # déjà traité lors d'un passage interrompu
                root.clear()
                continue
            a = el.attrib
            if tag == "Record":
                _record(a, agg, body)
            else:
                w = _workout(el)
                if w:
                    workouts.append(w)
            root.clear()  # libère la mémoire : l'export peut contenir des millions d'éléments
            if n % CHECKPOINT_EVERY == 0:
                save_state(n)
                if progress:
                    progress(n)

    batch = Batch(daily=agg.result(), workouts=workouts, weights=list(body.values()))
    for d in batch.daily.values():
        d["origine"] = "export_apple"
    if checkpoint and checkpoint.exists():
        checkpoint.unlink()
    return batch


def _record(a, agg: m.DayAggregator, body: dict):
    typ = a.get("type", "")
    src = a.get("sourceName", "")
    start = m.parse_ts(a.get("startDate"))
    if not start:
        return
    if typ in QUANTITY:
        col, conv = QUANTITY[typ]
        v = _f(a.get("value"))
        if v is None:
            return
        if conv:
            v = conv(v, a.get("unit"))
        agg.add(col, start.date(), v, source=src, ts=start)
    elif typ == Q + "HeartRate":
        v = _f(a.get("value"))
        if v is not None:
            agg.add("fc_moyenne_bpm", start.date(), v)
            agg.add("fc_min_bpm", start.date(), v)
            agg.add("fc_max_bpm", start.date(), v)
    elif typ == SLEEP:
        stage = SLEEP_VALUES.get(a.get("value", ""), "asleep")
        agg.add_sleep_segment(start, m.parse_ts(a.get("endDate")), stage, src)
    elif typ == STAND:
        if a.get("value") == "HKCategoryValueAppleStandHourStood":
            agg.add("heures_debout", start.date(), 1.0, source=src)
    elif typ in BODY:
        col, conv = BODY[typ]
        v = _f(a.get("value"))
        if v is None:
            return
        if conv:
            v = conv(v, a.get("unit"))
        key = m.weight_id(start)
        row = body.setdefault(key, {"id": key, "date": start.date().isoformat(),
                                    "heure": start.strftime("%H:%M:%S"), "granularite": "mesure",
                                    "source": src, "origine": "export_apple"})
        row[col] = v


def _workout(el) -> dict | None:
    a = el.attrib
    start, end = m.parse_ts(a.get("startDate")), m.parse_ts(a.get("endDate"))
    if not start:
        return None
    typ = a.get("workoutActivityType", "").replace("HKWorkoutActivityType", "")
    dur = _f(a.get("duration"))
    dur_min = m.to_minutes(dur, a.get("durationUnit", "min")) if dur is not None else None
    kcal = _f(a.get("totalEnergyBurned"))
    kcal = m.to_kcal(kcal, a.get("totalEnergyBurnedUnit")) if kcal is not None else None
    dist = _f(a.get("totalDistance"))
    dist = m.to_km(dist, a.get("totalDistanceUnit")) if dist is not None else None
    avg = mx = None
    for st in el.findall("WorkoutStatistics"):
        t = st.get("type", "")
        if t.endswith("ActiveEnergyBurned") and kcal is None:
            v = _f(st.get("sum"))
            kcal = m.to_kcal(v, st.get("unit")) if v is not None else None
        elif t.endswith(("DistanceWalkingRunning", "DistanceCycling", "DistanceSwimming")) and dist is None:
            v = _f(st.get("sum"))
            dist = m.to_km(v, st.get("unit")) if v is not None else None
        elif t.endswith("HeartRate"):
            avg, mx = _f(st.get("average")), _f(st.get("maximum"))
    return {
        "id": m.workout_id(start), "date": start.date().isoformat(),
        "debut": start.strftime("%Y-%m-%d %H:%M:%S"), "fin": end.strftime("%Y-%m-%d %H:%M:%S") if end else None,
        "type": WORKOUT_FR.get(typ, typ or "Activité"), "duree_min": dur_min, "distance_km": dist,
        "calories_kcal": kcal, "fc_moyenne_bpm": avg, "fc_max_bpm": mx,
        "source": a.get("sourceName", ""), "id_service": "", "origine": "export_apple",
    }
