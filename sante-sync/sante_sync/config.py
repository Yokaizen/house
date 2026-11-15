"""Emplacements et configuration.

Le code et l'état interne vivent dans le dossier applicatif (hors du dossier
synchronisé). Les données vivent dans le dossier de données (synchronisé).
Aucun secret n'est stocké ici : voir secrets.py (trousseau du système).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def app_dir() -> Path:
    """Dossier applicatif : code, environnement Python, état, journaux."""
    env = os.environ.get("SANTE_SYNC_HOME")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "SanteSync"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SanteSync"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "sante-sync"


def default_icloud_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", Path.home())) / "iCloudDrive"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    return Path.home() / "iCloudDrive"


@dataclass
class Config:
    data_dir: str = ""
    # Dossiers où Health Auto Export dépose ses fichiers. Vide = détection auto.
    hae_dirs: list[str] = field(default_factory=list)
    run_after: str = "08:30"          # pas de collecte automatique avant cette heure
    stale_hours: float = 36.0         # au-delà, l'export iPhone est jugé en retard
    retry_delays: list[float] = field(default_factory=lambda: [30.0, 120.0])  # 3 essais
    activity_reload_days: int = 3
    weight_reload_margin_days: int = 7
    owner: str = ""

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    def save(self) -> Path:
        p = config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
        return p


def config_path() -> Path:
    return app_dir() / "config.json"


def state_dir() -> Path:
    d = app_dir() / "etat"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_dir() -> Path:
    d = app_dir() / "journaux"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_config() -> Config:
    p = config_path()
    if not p.exists():
        raise SystemExit(
            f"Configuration absente ({p}). Lancez d'abord : python -m sante_sync configurer --data-dir <dossier>"
        )
    raw = json.loads(p.read_text(encoding="utf-8"))
    known = {k: v for k, v in raw.items() if k in Config.__dataclass_fields__}
    return Config(**known)


def detect_hae_dirs(icloud: Path | None = None) -> list[Path]:
    """Cherche le dossier où Health Auto Export écrit dans iCloud Drive.

    D'après la documentation de l'éditeur : iCloud Drive → Auto Export → <nom
    de l'automatisation>. Sous Windows, le dossier d'une app peut aussi
    apparaître sous un nom technique (iCloud~…HealthExport…).
    """
    icloud = icloud or default_icloud_dir()
    found: list[Path] = []
    if not icloud.exists():
        return found
    try:
        children = list(icloud.iterdir())
    except OSError:
        return found
    for child in children:
        name = child.name.lower()
        if not child.is_dir():
            continue
        if name in ("auto export", "health auto export") or ("healthexport" in name.replace(" ", "")
                                                              and name.startswith("icloud~")):
            found.append(child)
    return found
