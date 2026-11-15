"""Orchestration : sources, essais répétés, status.json, notifications."""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from . import apple_xml, hae
from . import model as m
from .config import Config, detect_hae_dirs, state_dir
from .notify import notify
from .store import Table, fmt

log = logging.getLogger("sante_sync")

IMPORT_DIR = "import_manuel"
DONE_DIR = "integres"


class NotYetConfigured(Exception):
    """La source n'a jamais fonctionné et son dossier n'existe pas encore."""


class SourceWarning(Exception):
    """La source a tourné mais quelque chose mérite votre attention."""


@dataclass
class Result:
    etat: str = "ok"                  # ok | avertissement | erreur | ignoree
    message: str = ""
    lignes: dict[str, int] = field(default_factory=dict)
    details: dict = field(default_factory=dict)
    essais: int = 1


def now_local() -> datetime:
    return datetime.now().astimezone()


# ------------------------------------------------------------ état interne

def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name("." + p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(tmp, p)


class Ledger:
    """Mémoire des fichiers déjà intégrés (dans le dossier applicatif)."""

    def __init__(self, name: str):
        self.path = state_dir() / name
        self.data = _read_json(self.path, {})

    def changed(self, f: Path) -> bool:
        st = f.stat()
        e = self.data.get(str(f))
        return not e or e.get("mtime") != st.st_mtime or e.get("size") != st.st_size

    def max_date(self, f: Path) -> str:
        return (self.data.get(str(f)) or {}).get("max_date", "")

    def record(self, f: Path, dates: set[date]) -> None:
        st = f.stat()
        self.data[str(f)] = {"mtime": st.st_mtime, "size": st.st_size,
                             "min_date": min(dates).isoformat() if dates else "",
                             "max_date": max(dates).isoformat() if dates else "",
                             "integre_le": now_local().isoformat(timespec="seconds")}

    def save(self) -> None:
        _write_json(self.path, self.data)


# ------------------------------------------------------------ application

def apply_batch(tables: dict[str, Table], batch: hae.Batch) -> dict[str, int]:
    """Écrit un lot dans les tables (en mémoire). Retourne les lignes modifiées par fichier."""
    daily, workouts, weights = tables["daily"], tables["workouts"], tables["weights"]
    changed_daily = daily.upsert({"date": d.isoformat(), **v} for d, v in batch.daily.items())
    changed_w = workouts.upsert(batch.workouts)
    changed_p = weights.upsert(batch.weights)

    # Une vraie pesée rend inutile la « moyenne du jour » éventuelle du même jour.
    real_days = {r["date"] for r in weights.rows.values() if r.get("granularite") == "mesure"}
    removed = weights.delete([k for k, r in list(weights.rows.items())
                              if r.get("granularite") == "moyenne_jour" and r.get("date") in real_days])
    changed_p |= removed

    # Résumé des activités du jour, recalculé depuis la table des activités.
    days = {workouts.rows[k]["date"] for k in changed_w if k in workouts.rows}
    if days:
        by_day: dict[str, list] = {}
        for r in workouts.rows.values():
            if r["date"] in days:
                by_day.setdefault(r["date"], []).append(r)
        recs = []
        for d, rows in by_day.items():
            rows.sort(key=lambda r: r["debut"])
            mins = sum(float(r["duree_min"]) for r in rows if r["duree_min"])
            label = ", ".join(f"{r['type']} {round(float(r['duree_min']))} min" if r["duree_min"] else r["type"]
                              for r in rows)
            # Origine de la ligne inchangée : on complète seulement le résumé d'activité.
            existing = daily.get(d)
            recs.append({"date": d, "nb_activites": len(rows), "minutes_activites": mins, "activites": label,
                         "origine": existing.get("origine", "") if existing else rows[0]["origine"]})
        # écriture directe : le résumé reflète toujours la table d'activités
        for rec in recs:
            row = daily.rows.get(rec["date"])
            before = dict(row) if row else None
            if row is None:
                daily.upsert([rec])
            else:
                row["nb_activites"] = str(rec["nb_activites"])
                row["minutes_activites"] = fmt(float(rec["minutes_activites"]), 0)
                row["activites"] = rec["activites"]
            if daily.rows[rec["date"]] != before:
                changed_daily.add(rec["date"])
    return {m.DAILY_FILE: len(changed_daily), m.WORKOUT_FILE: len(changed_w), m.WEIGHT_FILE: len(changed_p)}


def _add(acc: dict[str, int], more: dict[str, int]) -> None:
    for k, v in more.items():
        acc[k] = acc.get(k, 0) + v


# ------------------------------------------------------------ sources

class Source:
    name = ""
    label = ""

    def run(self, ctx: "Context") -> Result:  # pragma: no cover
        raise NotImplementedError


@dataclass
class Context:
    cfg: Config
    tables: dict[str, Table]
    backfill: bool = False
    today: date = field(default_factory=date.today)
    previous_ok: dict = field(default_factory=dict)


def hae_files(dirs: list[Path]) -> list[Path]:
    files = []
    for d in dirs:
        for p in d.rglob("*"):
            if not p.is_file() or p.name.startswith("."):
                continue
            if any(part.lower() == "automations" for part in p.relative_to(d).parts[:-1]):
                continue  # sauvegarde des réglages de l'app, pas des données
            if p.suffix.lower() == ".json" and hae.looks_like_hae_json(p):
                files.append(p)
            elif p.suffix.lower() == ".csv":
                files.append(p)
    return sorted(files, key=lambda p: (p.stat().st_mtime, p.name))


class AppleHealthSource(Source):
    """Fichiers déposés chaque jour dans iCloud Drive par Health Auto Export."""
    name = "apple_sante"
    label = "Apple Santé (Health Auto Export)"

    def run(self, ctx: Context) -> Result:
        cfg = ctx.cfg
        # Détection : à côté du dossier de données (tous deux dans iCloud Drive), sinon iCloud Drive par défaut.
        dirs = [Path(d) for d in cfg.hae_dirs] if cfg.hae_dirs else (
            detect_hae_dirs(cfg.data_path.parent) or detect_hae_dirs())
        dirs = [d for d in dirs if d.exists()]
        if not dirs:
            raise NotYetConfigured("Dossier de Health Auto Export introuvable dans iCloud Drive "
                               "(iCloud Drive → Auto Export). L'automatisation est-elle créée sur l'iPhone, "
                               "et iCloud pour Windows est-il ouvert ?")
        files = hae_files(dirs)
        if not files:
            raise RuntimeError(f"Aucun fichier d'export dans {', '.join(map(str, dirs))}")

        ledger = Ledger("fichiers_apple_sante.json")
        progress_path = state_dir() / "historique_en_cours.json"
        progress = _read_json(progress_path, {"faits": []}) if ctx.backfill else {"faits": []}
        if ctx.backfill:
            # Reprise : on saute les fichiers déjà traités par un historique interrompu.
            todo = [f for f in files if str(f) not in set(progress["faits"])]
            if len(todo) < len(files):
                log.info("Reprise de l'historique : %d fichier(s) déjà faits, %d restant(s)",
                         len(files) - len(todo), len(todo))
        else:
            cutoff = ctx.today - timedelta(days=cfg.activity_reload_days)
            last_w = max((r["date"] for r in ctx.tables["weights"].rows.values()), default="")
            if last_w:
                cutoff = min(cutoff, date.fromisoformat(last_w) - timedelta(days=cfg.weight_reload_margin_days))
            todo = [f for f in files if ledger.changed(f) or ledger.max_date(f) >= cutoff.isoformat()]

        lignes: dict[str, int] = {}
        bad = []
        ignored: set[str] = set()
        seen = {"jours": 0, "seances": 0, "pesees": 0}
        for f in todo:
            try:
                batch = hae.parse_file(f)
            except (ValueError, UnicodeDecodeError) as exc:  # fichier en cours de synchronisation ou abîmé
                bad.append(f"{f.name} ({exc})")
                continue
            _add(lignes, apply_batch(ctx.tables, batch))
            ledger.record(f, batch.dates())
            ignored |= batch.ignored
            seen["jours"] += len(batch.daily)
            seen["seances"] += len(batch.workouts)
            seen["pesees"] += len(batch.weights)
            if ctx.backfill:
                progress["faits"].append(str(f))
                if len(progress["faits"]) % 20 == 0:  # point de reprise
                    for t in ctx.tables.values():
                        t.save()
                    ledger.save()
                    _write_json(progress_path, progress)
        ledger.save()
        if ctx.backfill:
            progress_path.unlink(missing_ok=True)
        if todo and len(bad) == len(todo):
            raise RuntimeError("Aucun fichier lisible : " + "; ".join(bad[:3]))

        newest = max(f.stat().st_mtime for f in files)
        newest_dt = datetime.fromtimestamp(newest)
        age_h = (datetime.now() - newest_dt).total_seconds() / 3600
        res = Result(lignes=lignes, details={
            "dossiers": [str(d) for d in dirs], "fichiers_lus": len(todo), "fichiers_disponibles": len(files),
            "dernier_export_recu": newest_dt.isoformat(timespec="minutes"),
            "elements_lus": seen,
            # Utile si l'app change un nom : ces mesures sont reçues mais pas encore reprises dans les CSV.
            "mesures_non_reconnues": sorted(ignored),
        })
        msgs = [f"{len(todo)} fichier(s) lu(s)"]
        if bad:
            res.etat = "avertissement"
            msgs.append("illisibles : " + "; ".join(bad[:3]))
        if age_h > cfg.stale_hours:
            res.etat = "avertissement"
            msgs.append(f"dernier export de l'iPhone reçu il y a {age_h:.0f} h : ouvrez Health Auto Export "
                        "sur l'iPhone (déverrouillé) pour relancer l'export")
        res.message = " ; ".join(msgs)
        return res


class ManualImportSource(Source):
    """Fichiers déposés à la main dans import_manuel/ (export Apple ou Health Auto Export)."""
    name = "import_manuel"
    label = "Import manuel"

    def run(self, ctx: Context) -> Result:
        inbox = ctx.cfg.data_path / IMPORT_DIR
        done = inbox / DONE_DIR
        inbox.mkdir(parents=True, exist_ok=True)
        files = sorted(p for p in inbox.iterdir()
                       if p.is_file() and not p.name.startswith(".") and p.name.upper() != "LISEZMOI.TXT")
        if not files:
            return Result(etat="ok", message="aucun fichier à intégrer")
        lignes: dict[str, int] = {}
        ok, bad = [], []
        for f in files:
            try:
                if apple_xml.is_apple_export(f):
                    ck = state_dir() / f"reprise_{m.short_hash(f.name, f.stat().st_size)}.pkl"
                    batch = apple_xml.parse_export(f, checkpoint=ck,
                                                   progress=lambda n: log.info("  … %d éléments lus", n))
                elif f.suffix.lower() in (".json", ".csv"):
                    batch = hae.parse_file(f)
                else:
                    raise ValueError("format non reconnu (attendu : export.zip d'Apple Santé, .json ou .csv)")
            except Exception as exc:
                bad.append(f"{f.name} : {exc}")
                continue
            _add(lignes, apply_batch(ctx.tables, batch))
            # Les tables sont écrites avant de déplacer le fichier : rien ne se perd si on est interrompu.
            for t in ctx.tables.values():
                t.save()
            done.mkdir(exist_ok=True)
            shutil.move(str(f), str(done / f"{now_local():%Y%m%d-%H%M%S}_{f.name}"))
            ok.append(f.name)
        res = Result(lignes=lignes, details={"integres": ok, "refuses": bad})
        if bad:
            res.etat = "erreur" if not ok else "avertissement"
            res.message = f"{len(ok)} intégré(s), {len(bad)} refusé(s) : " + "; ".join(bad)
        else:
            res.message = f"{len(ok)} fichier(s) intégré(s) : " + ", ".join(ok)
        return res


class SimulatedFailure(Source):
    def __init__(self, inner: Source):
        self.inner = inner
        self.name, self.label = inner.name, inner.label

    def run(self, ctx: Context) -> Result:
        raise RuntimeError("Panne simulée pour test (option --simuler-panne)")


def all_sources() -> list[Source]:
    return [AppleHealthSource(), ManualImportSource()]


# ------------------------------------------------------------ passage complet

class AlreadyRunning(Exception):
    pass


class Lock:
    def __init__(self):
        self.path = state_dir() / "collecte.lock"

    def __enter__(self):
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            age = time.time() - self.path.stat().st_mtime
            if age < 3 * 3600:
                raise AlreadyRunning(f"Une collecte est déjà en cours ({self.path})")
            self.path.unlink(missing_ok=True)  # verrou abandonné
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)


def _run_with_retries(src: Source, ctx: Context, delays: list[float]) -> Result:
    attempts = len(delays) + 1
    last_exc = None
    for i in range(attempts):
        try:
            res = src.run(ctx)
            res.essais = i + 1
            return res
        except NotYetConfigured as exc:
            if not ctx.previous_ok.get(src.name):
                # Jamais fonctionné : on attend l'installation côté iPhone, sans alerte ni nouvel essai.
                return Result(etat="en_attente", message="En attente des premiers exports de l'iPhone. " + str(exc))
            last_exc = exc
            log.error("%s : essai %d/%d échoué : %s", src.name, i + 1, attempts, exc)
            if i < len(delays):
                time.sleep(delays[i])
        except Exception as exc:
            last_exc = exc
            log.error("%s : essai %d/%d échoué : %s", src.name, i + 1, attempts, exc)
            if i < len(delays):
                time.sleep(delays[i])
    return Result(etat="erreur", message=str(last_exc), essais=attempts)


def file_summary(t: Table) -> dict:
    keys = sorted(t.rows)
    dates = sorted(r.get("date", "") for r in t.rows.values() if r.get("date"))
    return {"lignes": len(keys), "premiere_date": dates[0] if dates else None,
            "derniere_date": dates[-1] if dates else None}


def collect(cfg: Config, *, force: bool = False, backfill: bool = False,
            simulate_fail: set[str] | None = None, only: set[str] | None = None) -> dict | None:
    """Un passage. Retourne le contenu de status.json, ou None si rien à faire."""
    st_path = state_dir() / "dernier_succes.json"
    st = _read_json(st_path, {})
    today = date.today().isoformat()
    if not force and not backfill:
        hh, mm = map(int, cfg.run_after.split(":"))
        if datetime.now().time() < datetime.now().replace(hour=hh, minute=mm).time():
            log.info("Avant %s : pas de collecte automatique.", cfg.run_after)
            return None
        if st.get("date") == today:
            log.info("Déjà un passage réussi aujourd'hui (%s) : rien à faire.", st.get("heure"))
            return None

    data_dir = cfg.data_path
    data_dir.mkdir(parents=True, exist_ok=True)
    from .docs import ensure_docs
    ensure_docs(cfg)

    with Lock():
        tables = m.open_tables(data_dir)
        status_path = data_dir / "status.json"
        previous = _read_json(status_path, {})
        ctx = Context(cfg=cfg, tables=tables, backfill=backfill,
                      previous_ok={k: v.get("derniere_reussite_source")
                                   for k, v in (previous.get("sources") or {}).items()})
        started = now_local()
        sources_status = {}
        for src in all_sources():
            if only and src.name not in only:
                continue
            if simulate_fail and src.name in simulate_fail:
                src = SimulatedFailure(src)
            log.info("Source %s…", src.name)
            res = _run_with_retries(src, ctx, cfg.retry_delays)
            if res.etat != "erreur":
                for t in tables.values():
                    t.save()
            prev = (previous.get("sources") or {}).get(src.name, {})
            entry = {
                "libelle": src.label, "etat": res.etat, "message": res.message,
                "lignes_mises_a_jour": res.lignes, "essais": res.essais,
                "derniere_reussite": started.isoformat(timespec="seconds") if res.etat in ("ok", "avertissement")
                else prev.get("derniere_reussite"),
                # a déjà réellement fonctionné au moins une fois (sert à distinguer « pas encore installé »)
                "derniere_reussite_source": started.isoformat(timespec="seconds") if res.etat in ("ok", "avertissement")
                else prev.get("derniere_reussite_source"),
                **res.details,
            }
            sources_status[src.name] = entry
            log.info("  → %s : %s", res.etat, res.message)
            if res.etat in ("erreur", "avertissement"):
                _notify_once(src, res)

        overall = "ok" if all(s["etat"] in ("ok", "en_attente") for s in sources_status.values()) else (
            "erreur" if all(s["etat"] == "erreur" for s in sources_status.values()) else "partiel")
        status = {
            "derniere_execution": started.isoformat(timespec="seconds"),
            "fin_execution": now_local().isoformat(timespec="seconds"),
            "resultat": overall,
            "mode": "historique" if backfill else ("force" if force else "automatique"),
            "dernier_passage_entierement_reussi": (started.isoformat(timespec="seconds") if overall == "ok"
                                                   else previous.get("dernier_passage_entierement_reussi")),
            "sources": sources_status,
            "fichiers": {
                m.DAILY_FILE: file_summary(tables["daily"]),
                m.WORKOUT_FILE: file_summary(tables["workouts"]),
                m.WEIGHT_FILE: file_summary(tables["weights"]),
            },
            "a_lire": "Données fraîches si resultat=ok et fichiers.apple_quotidien.csv.derniere_date "
                      "= aujourd'hui ou hier. Voir AGENTS.md.",
        }
        _write_json(status_path, status)
        if overall == "ok" and not backfill:
            _write_json(st_path, {"date": today, "heure": started.strftime("%H:%M:%S")})
        return status


def _notify_once(src: Source, res: Result) -> None:
    """Une seule notification par jour et par problème, pour ne pas vous harceler
    lors des relances automatiques de la journée."""
    p = state_dir() / "notifications.json"
    data = _read_json(p, {})
    today = date.today().isoformat()
    sent = data.get(today, [])
    key = f"{src.name}:{res.etat}"
    if key in sent:
        return
    title = f"Santé : {src.label} — {'erreur' if res.etat == 'erreur' else 'à vérifier'}"
    notify(title, res.message[:240])
    _write_json(p, {today: sent + [key]})
