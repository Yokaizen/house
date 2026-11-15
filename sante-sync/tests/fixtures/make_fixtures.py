"""Génère des fichiers de démonstration au format réel de Health Auto Export
(JSON v2, documentation de l'éditeur) et de l'export complet Apple Santé.
Valeurs synthétiques, réalistes, déterministes."""
from __future__ import annotations

import json
import random
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

TZ = "+0100"


def ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S ") + TZ


def hae_day(d: date, rnd: random.Random, *, with_workout=True, missing=()) -> dict:
    """Un fichier « Day » avec Summarize Data activé (regroupement par jour)."""
    midnight = datetime.combine(d, datetime.min.time())
    src = "Apple Watch de Yann|iPhone de Yann"
    metrics = []

    def add(name, units, qty, source=src):
        if name in missing:
            return
        metrics.append({"name": name, "units": units, "data": [{"date": ts(midnight), "qty": qty, "source": source}]})

    add("step_count", "count", rnd.randint(4500, 14000))
    add("walking_running_distance", "km", round(rnd.uniform(3, 10), 3))
    add("active_energy", "kJ", round(rnd.uniform(1200, 3200), 1))
    add("basal_energy_burned", "kcal", round(rnd.uniform(1650, 1750), 1))
    add("apple_exercise_time", "min", rnd.randint(10, 70))
    add("apple_stand_hour", "count", rnd.randint(8, 14))
    add("flights_climbed", "count", rnd.randint(2, 15))
    add("resting_heart_rate", "count/min", rnd.randint(52, 62), "Apple Watch de Yann")
    add("heart_rate_variability", "ms", round(rnd.uniform(30, 60), 1), "Apple Watch de Yann")
    add("respiratory_rate", "count/min", round(rnd.uniform(13, 16), 1), "Apple Watch de Yann")
    add("blood_oxygen_saturation", "%", round(rnd.uniform(95, 99), 1), "Apple Watch de Yann")
    add("vo2_max", "ml/(kg·min)", round(rnd.uniform(40, 43), 2), "Apple Watch de Yann")
    if "heart_rate" not in missing:
        metrics.append({"name": "heart_rate", "units": "count/min", "data": [
            {"date": ts(midnight), "Min": rnd.randint(45, 52), "Avg": rnd.randint(68, 78),
             "Max": rnd.randint(130, 170), "source": "Apple Watch de Yann"}]})
    if "sleep_analysis" not in missing:
        bed = midnight - timedelta(minutes=rnd.randint(30, 90))
        core, deep, rem, awake = rnd.uniform(3.2, 4.2), rnd.uniform(0.6, 1.3), rnd.uniform(1.2, 2.0), rnd.uniform(0.1, 0.5)
        total = core + deep + rem
        end = bed + timedelta(hours=total + awake)
        metrics.append({"name": "sleep_analysis", "units": "hr", "data": [{
            "date": ts(midnight), "totalSleep": round(total, 3), "asleep": 0, "core": round(core, 3),
            "deep": round(deep, 3), "rem": round(rem, 3), "sleepStart": ts(bed), "sleepEnd": ts(end),
            "inBed": round(total + awake + 0.2, 3), "inBedStart": ts(bed - timedelta(minutes=10)),
            "inBedEnd": ts(end + timedelta(minutes=5)), "awake": round(awake, 3), "source": "Apple Watch de Yann"}]})
    workouts = []
    if with_workout:
        start = midnight + timedelta(hours=18, minutes=rnd.randint(0, 50))
        dur = rnd.randint(1500, 3600)
        workouts.append({
            "id": f"0A1B2C3D-{d:%Y%m%d}-4E5F-9999-000000000001", "name": rnd.choice(["Course en extérieur", "Marche en extérieur"]),
            "start": ts(start), "end": ts(start + timedelta(seconds=dur)), "duration": dur,
            "activeEnergyBurned": {"qty": round(dur / 60 * 9.5, 1), "units": "kcal"},
            "distance": {"qty": round(dur / 360, 2), "units": "km"},
            "avgHeartRate": {"qty": rnd.randint(130, 150), "units": "count/min"},
            "maxHeartRate": {"qty": rnd.randint(160, 175), "units": "count/min"},
        })
    return {"data": {"metrics": metrics, "workouts": workouts}}


def hae_weights(d: date, rnd: random.Random, kg: float) -> dict:
    """Automatisation « Mesures » : Summarize Data désactivé (une ligne par pesée)."""
    t = datetime.combine(d, datetime.min.time()) + timedelta(hours=7, minutes=rnd.randint(0, 40), seconds=rnd.randint(0, 59))
    return {"data": {"metrics": [{"name": "weight_body_mass", "units": "kg",
                                  "data": [{"date": ts(t), "qty": round(kg, 2), "source": "Santé"}]}], "workouts": []}}


def write_hae_tree(root: Path, days: list[date], seed=7, weigh_every=3) -> list[Path]:
    rnd = random.Random(seed)
    out = []
    daily = root / "Auto Export" / "Sante-Quotidien"
    meas = root / "Auto Export" / "Sante-Mesures"
    daily.mkdir(parents=True, exist_ok=True)
    meas.mkdir(parents=True, exist_ok=True)
    (root / "Auto Export" / "Automations").mkdir(parents=True, exist_ok=True)
    (root / "Auto Export" / "Automations" / "Sante-Quotidien.json").write_text(
        json.dumps({"automationName": "Sante-Quotidien", "type": "iCloudDrive", "data": {"x": 1}}), encoding="utf-8")
    kg = 82.4
    for i, d in enumerate(days):
        p = daily / f"HealthAutoExport-{d.isoformat()}.json"
        p.write_text(json.dumps(hae_day(d, rnd, with_workout=(i % 2 == 0)), ensure_ascii=False), encoding="utf-8")
        out.append(p)
        kg -= rnd.uniform(-0.2, 0.35)
        if i % weigh_every == 0:
            q = meas / f"HealthAutoExport-{d.isoformat()}.json"
            q.write_text(json.dumps(hae_weights(d, rnd, kg)), encoding="utf-8")
            out.append(q)
    return out


def apple_export_zip(path: Path, start: date, ndays: int, seed=3) -> Path:
    """Petit export.zip au format officiel, avec doublons montre/iPhone sur les pas."""
    rnd = random.Random(seed)
    recs = []
    for i in range(ndays):
        d = start + timedelta(days=i)
        base = datetime.combine(d, datetime.min.time())
        for h in range(8, 20, 2):
            t0, t1 = base + timedelta(hours=h), base + timedelta(hours=h, minutes=50)
            n = rnd.randint(300, 1200)
            recs.append(("HKQuantityTypeIdentifierStepCount", "Apple Watch de Yann", "count", n, t0, t1))
            recs.append(("HKQuantityTypeIdentifierStepCount", "iPhone de Yann", "count", int(n * 0.8), t0, t1))
        recs.append(("HKQuantityTypeIdentifierRestingHeartRate", "Apple Watch de Yann", "count/min",
                     rnd.randint(55, 64), base + timedelta(hours=12), base + timedelta(hours=12)))
        recs.append(("HKQuantityTypeIdentifierHeartRateVariabilitySDNN", "Apple Watch de Yann", "ms",
                     round(rnd.uniform(28, 55), 1), base + timedelta(hours=3), base + timedelta(hours=3, minutes=1)))
        recs.append(("HKQuantityTypeIdentifierOxygenSaturation", "Apple Watch de Yann", "%",
                     0.97, base + timedelta(hours=4), base + timedelta(hours=4)))
        s = base - timedelta(hours=1)
        for stage, mins in (("AsleepCore", 120), ("AsleepDeep", 60), ("AsleepREM", 90), ("Awake", 10), ("AsleepCore", 110)):
            e = s + timedelta(minutes=mins)
            recs.append(("HKCategoryTypeIdentifierSleepAnalysis", "Apple Watch de Yann", None,
                         "HKCategoryValueSleepAnalysis" + stage, s, e))
            s = e
        if i % 4 == 0:
            t = base + timedelta(hours=7, minutes=12)
            recs.append(("HKQuantityTypeIdentifierBodyMass", "Santé", "lb", round(185 - i * 0.1, 1), t, t))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<!DOCTYPE HealthData [<!ELEMENT HealthData ANY>]>',
             '<HealthData locale="fr_FR">', ' <ExportDate value="2026-11-15 08:00:00 +0100"/>',
             ' <Me HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexNotSet"/>']
    for typ, src, unit, val, t0, t1 in recs:
        u = f' unit="{unit}"' if unit else ""
        lines.append(f' <Record type="{typ}" sourceName="{src}" sourceVersion="11.0"{u} creationDate="{ts(t1)}" '
                     f'startDate="{ts(t0)}" endDate="{ts(t1)}" value="{val}">'
                     f'<MetadataEntry key="HKTimeZone" value="Europe/Paris"/></Record>')
    w0 = datetime.combine(start, datetime.min.time()) + timedelta(hours=18)
    lines.append(f' <Workout workoutActivityType="HKWorkoutActivityTypeRunning" duration="31.5" durationUnit="min" '
                 f'sourceName="Apple Watch de Yann" startDate="{ts(w0)}" endDate="{ts(w0 + timedelta(minutes=31.5))}">'
                 f'<WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="{ts(w0)}" '
                 f'endDate="{ts(w0)}" sum="312" unit="kcal"/>'
                 f'<WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" startDate="{ts(w0)}" '
                 f'endDate="{ts(w0)}" sum="5.2" unit="km"/>'
                 f'<WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" startDate="{ts(w0)}" '
                 f'endDate="{ts(w0)}" average="146" minimum="98" maximum="171" unit="count/min"/></Workout>')
    lines.append(' <ActivitySummary dateComponents="2020-01-01" activeEnergyBurned="400"/>')
    lines.append("</HealthData>")
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("apple_health_export/export.xml", "\n".join(lines))
        z.writestr("apple_health_export/export_cda.xml", "<ClinicalDocument/>")
    return path
