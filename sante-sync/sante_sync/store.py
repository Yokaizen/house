"""Tables CSV avec mise à jour sans doublon (upsert par clé).

Règles :
- une clé = une ligne (date pour le quotidien, identifiant pour les mesures) ;
- fusion champ par champ : une valeur absente de la nouvelle donnée n'efface
  jamais une valeur existante, et rien n'est jamais remplacé par zéro ;
- une origine moins fiable (ex. export complet Apple recalculé) ne fait que
  combler les cases vides d'une ligne venant d'une origine plus fiable ;
- écriture atomique (fichier temporaire puis renommage), pour que le dossier
  synchronisé ne voie jamais un fichier à moitié écrit.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterable

# Rang de fiabilité des origines (plus grand = prioritaire).
ORIGIN_RANK = {"": 0, "export_apple": 1, "hae": 2}


def fmt(value, decimals: int | None = None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        d = 2 if decimals is None else decimals
        s = f"{value:.{d}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(value)


class Table:
    def __init__(self, path: Path, key: str, columns: list[str],
                 decimals: dict[str, int] | None = None, origin_col: str | None = "origine"):
        self.path = Path(path)
        self.key = key
        self.columns = columns
        self.decimals = decimals or {}
        self.origin_col = origin_col if origin_col in columns else None
        self.rows: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                k = row.get(self.key)
                if k:
                    self.rows[k] = {c: (row.get(c) or "") for c in self.columns}

    def upsert(self, records: Iterable[dict]) -> set[str]:
        """Fusionne les enregistrements. Retourne les clés réellement modifiées."""
        changed: set[str] = set()
        for rec in records:
            k = fmt(rec.get(self.key))
            if not k:
                continue
            new = {c: fmt(rec[c], self.decimals.get(c)) for c in self.columns if c in rec and rec[c] is not None}
            old = self.rows.get(k)
            if old is None:
                row = {c: "" for c in self.columns}
                row.update(new)
                row[self.key] = k
                self.rows[k] = row
                changed.add(k)
                continue
            merged = dict(old)
            if self.origin_col:
                r_old = ORIGIN_RANK.get(old.get(self.origin_col, ""), 0)
                r_new = ORIGIN_RANK.get(new.get(self.origin_col, ""), 0)
            else:
                r_old = r_new = 0
            for c, v in new.items():
                if c == self.origin_col:
                    continue
                if v == "":
                    continue
                if r_new >= r_old or merged.get(c, "") == "":
                    merged[c] = v
            if self.origin_col and r_new > r_old:
                merged[self.origin_col] = new[self.origin_col]
            if merged != old:
                self.rows[k] = merged
                changed.add(k)
        return changed

    def delete(self, keys: Iterable[str]) -> set[str]:
        gone = {k for k in keys if self.rows.pop(k, None) is not None}
        return gone

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name("." + self.path.name + ".tmp")
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.columns, lineterminator="\n")
            w.writeheader()
            for k in sorted(self.rows):
                w.writerow(self.rows[k])
        os.replace(tmp, self.path)

    def get(self, key: str) -> dict[str, str] | None:
        return self.rows.get(key)

    def __len__(self) -> int:
        return len(self.rows)
