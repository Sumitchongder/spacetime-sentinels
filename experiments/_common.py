"""Shared helpers for the experiment scripts."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "data"
FIG = ROOT / "results" / "figures"
DATA.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

SEEDS = [7, 11, 13, 17, 19]
DEPTHS = [6, 12, 18]


def write_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    print(f"wrote {len(rows)} rows -> {path.relative_to(ROOT)}")


def slim(rec: dict) -> dict:
    drop = {"safe_sites", "check_columns", "sites", "supports"}
    return {k: v for k, v in rec.items() if k not in drop}
