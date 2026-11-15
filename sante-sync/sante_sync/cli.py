"""Ligne de commande : python -m sante_sync <commande>."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import __version__
from .config import Config, config_path, detect_hae_dirs, load_config, log_dir, state_dir


def _setup_logging(verbose: bool) -> None:
    root = logging.getLogger("sante_sync")
    root.setLevel(logging.INFO)
    fh = RotatingFileHandler(log_dir() / "sante-sync.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root.addHandler(fh)
    if verbose and sys.stderr is not None:  # pythonw n'a pas de console
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(sh)


def tail(path: Path, n: int = 5) -> str:
    if not path.exists():
        return f"{path.name} : (absent)"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return f"{path.name} : (vide)"
    head, body = rows[0], rows[1:]
    out = [f"== {path.name} — {len(body)} ligne(s), {n} dernières =="]
    for r in body[-n:]:
        out.append("  " + " | ".join(f"{h}={v}" for h, v in zip(head, r) if v != ""))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sante_sync", description="Collecte des données de santé vers des CSV.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("configurer", help="Créer ou modifier la configuration")
    c.add_argument("--data-dir", required=True)
    c.add_argument("--hae-dir", action="append", default=None, help="Dossier Health Auto Export (répétable)")
    c.add_argument("--heure", default=None, help="Heure de collecte, ex. 08:30")
    c.add_argument("--proprietaire", default=None)

    r = sub.add_parser("collecte", help="Passage quotidien")
    r.add_argument("--force", action="store_true", help="Ignorer l'heure et le « déjà fait aujourd'hui »")
    r.add_argument("--simuler-panne", action="append", default=[], metavar="SOURCE",
                   help="Test : faire échouer une source (apple_sante, import_manuel)")
    r.add_argument("-v", "--verbeux", action="store_true")

    h = sub.add_parser("historique", help="Récupérer tout l'historique (reprend s'il est interrompu)")
    h.add_argument("--recommencer", action="store_true", help="Oublier une reprise en cours")
    h.add_argument("-v", "--verbeux", action="store_true")

    sub.add_parser("statut", help="Afficher status.json et les dernières lignes")
    d = sub.add_parser("docs", help="(Ré)écrire README.md et AGENTS.md")
    d.add_argument("--regenerer", action="store_true")
    sub.add_parser("tester-notification", help="Envoyer une notification de test")
    sub.add_parser("diagnostic", help="Vérifier dossiers, trousseau et dernier passage")

    a = ap.parse_args(argv)

    if a.cmd == "configurer":
        try:
            cfg = load_config()
        except SystemExit:
            cfg = Config()
        cfg.data_dir = str(Path(a.data_dir).expanduser())
        if a.hae_dir is not None:
            cfg.hae_dirs = [str(Path(p).expanduser()) for p in a.hae_dir]
        if a.heure:
            cfg.run_after = a.heure
        if a.proprietaire:
            cfg.owner = a.proprietaire
        p = cfg.save()
        print(f"Configuration enregistrée : {p}")
        return 0

    cfg = load_config()
    verbose = getattr(a, "verbeux", False) or a.cmd in ("statut", "diagnostic")
    _setup_logging(verbose)
    from . import engine

    if a.cmd == "collecte":
        try:
            st = engine.collect(cfg, force=a.force, simulate_fail=set(a.simuler_panne))
        except engine.AlreadyRunning as exc:
            logging.getLogger("sante_sync").info(str(exc))
            return 0
        if st is None:
            return 0
        return 0 if st["resultat"] == "ok" else 1

    if a.cmd == "historique":
        if a.recommencer:
            for p in state_dir().glob("reprise_*.pkl"):
                p.unlink()
            (state_dir() / "historique_en_cours.json").unlink(missing_ok=True)
        st = engine.collect(cfg, backfill=True)
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return 0 if st and st["resultat"] != "erreur" else 1

    if a.cmd == "statut":
        sp = cfg.data_path / "status.json"
        print(sp.read_text(encoding="utf-8") if sp.exists() else "status.json absent : aucun passage encore.")
        from . import model as m
        for f in (m.DAILY_FILE, m.WORKOUT_FILE, m.WEIGHT_FILE):
            print(tail(cfg.data_path / f))
        return 0

    if a.cmd == "docs":
        from .docs import ensure_docs
        for p in ensure_docs(cfg, overwrite=a.regenerer):
            print(f"écrit : {p}")
        return 0

    if a.cmd == "tester-notification":
        from .notify import notify
        notify("Santé : test de notification", "Si vous lisez ceci, les alertes de la collecte vous parviendront.")
        return 0

    if a.cmd == "diagnostic":
        from .secrets import backend_name
        dirs = [Path(x) for x in cfg.hae_dirs] or detect_hae_dirs(cfg.data_path.parent) or detect_hae_dirs()
        print(f"Configuration : {config_path()}")
        print(f"Dossier de données : {cfg.data_dir} ({'présent' if cfg.data_path.exists() else 'ABSENT'})")
        print(f"Dossiers Health Auto Export : {', '.join(map(str, dirs)) or 'AUCUN TROUVÉ'}")
        if dirs:
            files = engine.hae_files([d for d in dirs if d.exists()])
            print(f"  fichiers d'export : {len(files)}" + (f", dernier : {files[-1].name}" if files else ""))
        print(f"Trousseau : {backend_name()}")
        print(f"Heure de collecte : {cfg.run_after}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
