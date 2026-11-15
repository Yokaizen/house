import csv
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_fixtures as fx  # noqa: E402

from sante_sync import apple_xml, engine, hae  # noqa: E402
from sante_sync import model as m  # noqa: E402
from sante_sync.config import Config  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SANTE_SYNC_HOME", str(tmp_path / "app"))
    monkeypatch.setenv("SANTE_SYNC_NOTIFY_LOG", str(tmp_path / "notifs.log"))
    icloud = tmp_path / "iCloudDrive"
    cfg = Config(data_dir=str(icloud / "Sante"), hae_dirs=[str(icloud / "Auto Export")],
                 retry_delays=[0.01, 0.01], run_after="00:00")
    cfg.save()
    return cfg, icloud, tmp_path


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def last_days(n):
    return [date.today() - timedelta(days=i) for i in range(n - 1, -1, -1)]


def test_parse_summarized_day_and_units():
    d = date(2026, 11, 10)
    obj = fx.hae_day(d, __import__("random").Random(1))
    b = hae.parse_json_obj(obj)
    row = b.daily[d]
    kj = next(x for x in obj["data"]["metrics"] if x["name"] == "active_energy")["data"][0]["qty"]
    assert row["calories_actives_kcal"] == pytest.approx(kj / 4.184)
    assert 4500 <= row["pas"] <= 14000
    assert row["sommeil_total_h"] > 4 and row["sommeil_profond_h"] > 0
    assert row["coucher"].startswith("2026-11-09") and row["lever"].startswith("2026-11-10")
    assert row["fc_min_bpm"] <= row["fc_moyenne_bpm"] <= row["fc_max_bpm"]
    assert b.workouts and b.workouts[0]["id"].startswith("act-20261110T18")


def test_multi_source_steps_not_double_counted_and_sleep_segments():
    obj = {"data": {"metrics": [
        {"name": "step_count", "units": "count", "data": [
            {"date": "2026-11-10 09:12:31 +0100", "qty": 1000, "source": "Apple Watch"},
            {"date": "2026-11-10 09:12:40 +0100", "qty": 800, "source": "iPhone"},
            {"date": "2026-11-10 15:02:11 +0100", "qty": 500, "source": "Apple Watch"}]},
        {"name": "sleep_analysis", "units": "hr", "data": [
            {"startDate": "2026-11-09 23:10:00 +0100", "endDate": "2026-11-10 01:10:00 +0100", "qty": 2,
             "value": "Core", "source": "Apple Watch"},
            {"startDate": "2026-11-10 01:10:00 +0100", "endDate": "2026-11-10 02:10:00 +0100", "qty": 1,
             "value": "Deep", "source": "Apple Watch"},
            {"startDate": "2026-11-10 02:10:00 +0100", "endDate": "2026-11-10 02:20:00 +0100", "qty": 0.17,
             "value": "Awake", "source": "Apple Watch"}]}]}}
    b = hae.parse_json_obj(obj)
    r = b.daily[date(2026, 11, 10)]
    assert r["pas"] == 1500  # montre seule, pas 2300
    assert r["sommeil_total_h"] == pytest.approx(3.0)
    assert r["sommeil_paradoxal_h"] == 0.0  # la montre mesure les phases : 0 réel
    assert r["coucher"] == "2026-11-09 23:10" and r["lever"] == "2026-11-10 02:10"


def test_missing_metric_stays_empty_never_zero(env):
    cfg, icloud, _ = env
    d = date.today()
    p = icloud / "Auto Export" / "Q" / "x.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(fx.hae_day(d, __import__("random").Random(2), missing=("heart_rate_variability", "sleep_analysis"))))
    engine.collect(cfg, force=True)
    r = rows(cfg.data_path / m.DAILY_FILE)[-1]
    assert r["vfc_sdnn_ms"] == "" and r["sommeil_total_h"] == "" and r["sommeil_profond_h"] == ""
    assert r["pas"] != ""


def test_full_run_idempotent_late_sync_and_catch_up(env):
    cfg, icloud, tmp = env
    days = last_days(10)
    fx.write_hae_tree(icloud, days[:7])
    st = engine.collect(cfg, force=True)
    assert st["resultat"] == "ok"
    assert st["sources"]["apple_sante"]["lignes_mises_a_jour"][m.DAILY_FILE] == 7
    daily = rows(cfg.data_path / m.DAILY_FILE)
    assert [r["date"] for r in daily] == [d.isoformat() for d in days[:7]]
    assert len(rows(cfg.data_path / m.WEIGHT_FILE)) == 3
    assert all(r["granularite"] == "mesure" for r in rows(cfg.data_path / m.WEIGHT_FILE))
    assert daily[0]["nb_activites"] == "1" and "min" in daily[0]["activites"]

    # Second passage sans rien de neuf : aucune ligne modifiée, aucun doublon.
    st2 = engine.collect(cfg, force=True)
    assert sum(st2["sources"]["apple_sante"]["lignes_mises_a_jour"].values()) == 0
    assert len(rows(cfg.data_path / m.DAILY_FILE)) == 7

    # La montre synchronise en retard : le fichier d'avant-hier est réécrit avec plus de pas.
    f = icloud / "Auto Export" / "Sante-Quotidien" / f"HealthAutoExport-{days[6].isoformat()}.json"
    obj = json.loads(f.read_text())
    steps = next(x for x in obj["data"]["metrics"] if x["name"] == "step_count")
    steps["data"][0]["qty"] = 20000
    f.write_text(json.dumps(obj))
    # + trois jours manqués (machine éteinte) arrivent d'un coup
    rnd = __import__("random").Random(9)
    for d in days[7:]:
        (f.parent / f"HealthAutoExport-{d.isoformat()}.json").write_text(json.dumps(fx.hae_day(d, rnd)))
    st3 = engine.collect(cfg, force=True)
    daily = rows(cfg.data_path / m.DAILY_FILE)
    assert len(daily) == 10
    assert next(r for r in daily if r["date"] == days[6].isoformat())["pas"] == "20000"
    assert st3["sources"]["apple_sante"]["lignes_mises_a_jour"][m.DAILY_FILE] == 4
    assert st3["fichiers"][m.DAILY_FILE]["derniere_date"] == days[-1].isoformat()


def test_settings_backup_folder_ignored(env):
    cfg, icloud, _ = env
    fx.write_hae_tree(icloud, last_days(2))
    files = engine.hae_files([icloud / "Auto Export"])
    assert not any("Automations" in str(f) for f in files)


def test_failure_isolated_status_and_notification(env):
    cfg, icloud, tmp = env
    fx.write_hae_tree(icloud, last_days(3))
    # un fichier déposé à la main doit être intégré même si l'autre source est en panne
    fx.apple_export_zip(cfg.data_path / "import_manuel" / "export.zip", date.today() - timedelta(days=60), 5)
    st = engine.collect(cfg, force=True, simulate_fail={"apple_sante"})
    a, i = st["sources"]["apple_sante"], st["sources"]["import_manuel"]
    assert a["etat"] == "erreur" and a["essais"] == 3 and "Panne simulée" in a["message"]
    assert i["etat"] == "ok" and i["lignes_mises_a_jour"][m.DAILY_FILE] == 5
    assert st["resultat"] == "partiel"
    notes = (tmp / "notifs.log").read_text(encoding="utf-8")
    assert "Apple Santé" in notes and "Panne simulée" in notes
    assert (cfg.data_path / "import_manuel" / "integres").exists()
    status = json.loads((cfg.data_path / "status.json").read_text(encoding="utf-8"))
    assert status["sources"]["apple_sante"]["etat"] == "erreur"
    # pas de deuxième notification le même jour pour le même problème
    engine.collect(cfg, force=True, simulate_fail={"apple_sante"})
    assert (tmp / "notifs.log").read_text(encoding="utf-8").count("Panne simulée") == 1


def test_missing_folder_is_an_error_not_a_crash(env):
    cfg, icloud, tmp = env
    st = engine.collect(cfg, force=True)
    assert st["sources"]["apple_sante"]["etat"] == "erreur"
    assert "introuvable" in st["sources"]["apple_sante"]["message"]
    assert st["sources"]["import_manuel"]["etat"] == "ok"


def test_stale_export_warns(env):
    cfg, icloud, tmp = env
    files = fx.write_hae_tree(icloud, last_days(2))
    old = (datetime.now() - timedelta(hours=50)).timestamp()
    for f in files:
        os.utime(f, (old, old))
    st = engine.collect(cfg, force=True)
    assert st["sources"]["apple_sante"]["etat"] == "avertissement"
    assert "il y a 50 h" in st["sources"]["apple_sante"]["message"]
    assert "Health Auto Export" in (tmp / "notifs.log").read_text(encoding="utf-8")


def test_once_per_day_and_not_before_hour(env):
    cfg, icloud, tmp = env
    fx.write_hae_tree(icloud, last_days(2))
    assert engine.collect(cfg)["resultat"] == "ok"
    assert engine.collect(cfg) is None  # déjà réussi aujourd'hui
    cfg.run_after = "23:59"
    (Path(os.environ["SANTE_SYNC_HOME"]) / "etat" / "dernier_succes.json").unlink()
    if datetime.now().strftime("%H:%M") < "23:59":
        assert engine.collect(cfg) is None


def test_apple_export_history_precedence_and_resume(env, monkeypatch):
    cfg, icloud, tmp = env
    start = date.today() - timedelta(days=20)
    z = fx.apple_export_zip(tmp / "export.zip", start, 20)
    # interruption au milieu, puis reprise
    monkeypatch.setattr(apple_xml, "CHECKPOINT_EVERY", 50)
    ck = tmp / "app" / "ck.pkl"
    calls = {"n": 0}

    def boom(n):
        calls["n"] += 1
        if calls["n"] == 2:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        apple_xml.parse_export(z, checkpoint=ck, progress=boom)
    assert ck.exists()
    resumed = apple_xml.parse_export(z, checkpoint=ck)
    full = apple_xml.parse_export(z)
    assert resumed.daily == full.daily and len(resumed.workouts) == len(full.workouts) == 1
    assert not ck.exists()
    d0 = full.daily[start]
    assert d0["sommeil_total_h"] == pytest.approx((120 + 60 + 90 + 110) / 60)
    assert d0["spo2_pct"] == pytest.approx(97)
    # montre + iPhone : on garde la montre, on n'additionne pas
    assert d0["pas"] < 1200 * 6 + 1
    w = full.weights[0]
    assert w["poids_kg"] == pytest.approx(185 * 0.45359237)

    # HAE pour les 3 derniers jours, puis import de l'export complet : HAE reste prioritaire
    fx.write_hae_tree(icloud, last_days(3))
    engine.collect(cfg, force=True)
    hae_row = {r["date"]: r for r in rows(cfg.data_path / m.DAILY_FILE)}[date.today().isoformat()]
    (cfg.data_path / "import_manuel").mkdir(parents=True, exist_ok=True)
    os.replace(z, cfg.data_path / "import_manuel" / "export.zip")
    st = engine.collect(cfg, backfill=True)
    daily = {r["date"]: r for r in rows(cfg.data_path / m.DAILY_FILE)}
    assert len(daily) == 21  # export : J-20..J-1, HAE : J-2..J
    yday = daily[(date.today() - timedelta(days=1)).isoformat()]
    assert yday["origine"] == "hae"
    assert daily[start.isoformat()]["origine"] == "export_apple"
    assert st["resultat"] == "ok"


def test_hae_csv_best_effort():
    text = ("Date/Time,Active Energy (kcal),Step Count (count),Resting Heart Rate (count/min),"
            "Heart Rate Variability (ms),Weight & Body Mass (lb),Sleep Analysis [Total] (hr)\n"
            "2026-11-10 00:00:00,512.3,9876,57,41.2,180,7.1\n"
            "2026-11-11 00:00:00,,4321,,,,\n")
    b = hae.parse_csv_text(text)
    assert b.daily[date(2026, 11, 10)]["pas"] == 9876
    assert "calories_actives_kcal" not in b.daily[date(2026, 11, 11)]
    assert b.weights[0]["poids_kg"] == pytest.approx(81.65, abs=0.01)


def test_daily_average_weight_replaced_by_real_measure(env):
    cfg, icloud, tmp = env
    tables = m.open_tables(cfg.data_path)
    engine.apply_batch(tables, hae.Batch(weights=[{"id": "pes-20261110T000000", "date": "2026-11-10",
                                                   "heure": "00:00:00", "poids_kg": 80.0,
                                                   "granularite": "moyenne_jour", "origine": "hae"}]))
    engine.apply_batch(tables, hae.Batch(weights=[{"id": "pes-20261110T071203", "date": "2026-11-10",
                                                   "heure": "07:12:03", "poids_kg": 80.1,
                                                   "granularite": "mesure", "origine": "hae"}]))
    assert list(tables["weights"].rows) == ["pes-20261110T071203"]
