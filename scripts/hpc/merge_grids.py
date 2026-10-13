"""Merge per-level grid files written by the Slurm array job into one file per profile."""

import json
import sys
from collections import defaultdict
from pathlib import Path

parts = sorted(Path(sys.argv[1] if len(sys.argv) > 1 else "results/data/parts").glob("grid_*_d*.json"))
by_profile = defaultdict(lambda: {"meta": None, "records": []})
for p in parts:
    blob = json.loads(p.read_text())
    name = blob["meta"]["profile"]["name"]
    tgt = by_profile[name]
    if tgt["meta"] is None:
        tgt["meta"] = blob["meta"]
        tgt["meta"]["specs"] = []
    tgt["meta"]["specs"].extend(blob["meta"]["specs"])
    tgt["records"].extend(blob["records"])
for name, blob in by_profile.items():
    out = Path("results/data") / f"grid_{name}.json"
    out.write_text(json.dumps(blob))
    print(f"{out}: {len(blob['records'])} records")
