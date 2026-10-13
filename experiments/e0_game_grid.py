"""E0: exhaustive sweep of the game's decision space (feeds the web game and E2-E4).

For each payload depth, each target set with at most ``budget`` checks, each
T count and each doping policy, evaluate the configuration exactly with Qiskit
Aer and store one JSON record.

Usage:
    python experiments/e0_game_grid.py --profile qff-synthetic --workers 2
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from sentinels import PayloadSpec, get_profile, run_grid

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="qff-synthetic")
    ap.add_argument("--depths", type=int, nargs="+", default=[6, 12, 18])
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--budget", type=int, default=4)
    ap.add_argument("--t-counts", type=int, nargs="+", default=[0, 1, 2, 4, 8, 16])
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--device", default="CPU", choices=["CPU", "GPU"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    profile = get_profile(args.profile)
    specs = [PayloadSpec(args.n, d, args.seed) for d in args.depths]
    t0 = time.perf_counter()
    records = run_grid(specs, profile, args.budget, args.t_counts, args.workers, args.device)
    out = Path(args.out) if args.out else ROOT / "results" / "data" / f"grid_{profile.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "profile": profile.__dict__,
        "specs": [s.__dict__ for s in specs],
        "budget": args.budget,
        "t_counts": args.t_counts,
        "wall_seconds": round(time.perf_counter() - t0, 1),
    }
    out.write_text(json.dumps({"meta": meta, "records": records}))
    print(f"wrote {len(records)} records to {out} in {meta['wall_seconds']} s")


if __name__ == "__main__":
    main()
