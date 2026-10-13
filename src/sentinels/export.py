"""Export Qiskit results to the JSON consumed by the web game (docs/data)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .payloads import brickwork_clifford, cz_layers
from .scoring import fidelity_rate

__all__ = ["export_web"]

_KEEP = [
    "targets", "k", "policy", "feasible", "F0", "F_ps", "keep", "R", "gain", "H0", "H_ps",
    "ancillas", "added_2q", "depth_2q", "depth_2q_bare", "n_safe_sites", "broken",
    "false_alarm", "sites", "safe_sites", "check_columns", "supports", "gamma", "reference",
]


def _round(x):
    if isinstance(x, float):
        return round(x, 5)
    if isinstance(x, list):
        return [_round(v) for v in x]
    return x


def _gates(n: int, depth: int, seed: int) -> list[list[list[str]]]:
    """Single-qubit gate labels after every CZ layer, read from the payload circuit."""
    qc = brickwork_clifford(n, depth, seed)
    per_layer = [[[] for _ in range(n)] for _ in range(depth)]
    sizes = [len(layer) for layer in cz_layers(n, depth)]
    layer, left = -1, 0
    for inst in qc.data:
        name = inst.operation.name
        if name == "cz":
            if left == 0:
                layer += 1
                left = sizes[layer]
            left -= 1
            continue
        if name == "h" or layer < 0:
            continue
        q = qc.find_bit(inst.qubits[0]).index
        per_layer[layer][q].append(name)
    return per_layer


def export_web(grid_files: list[Path], out_dir: Path) -> list[Path]:
    """Write one JSON per noise profile plus an index file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    index = {"profiles": []}
    for gf in grid_files:
        blob = json.loads(Path(gf).read_text())
        meta, recs = blob["meta"], blob["records"]
        prof = meta["profile"]
        levels = defaultdict(list)
        for r in recs:
            levels[(r["n"], r["depth"], r["payload_seed"], r["n_t"])].append(r)
        out_levels = []
        for (n, depth, seed, n_t), rs in sorted(levels.items()):
            configs = {}
            for r in rs:
                key = ",".join(map(str, r["targets"])) + "|" + r["policy"]
                configs[key] = {k: _round(r.get(k)) for k in _KEEP}
            feas = [r for r in rs if r["feasible"] and r["R"] is not None]
            best = max(feas, key=lambda r: r["R"])
            bare = next(r for r in rs if r["k"] == 0)
            best_b0 = max(feas, key=lambda r: fidelity_rate(r["F_ps"], r["keep"], 0.0))
            best_b1 = max(feas, key=lambda r: fidelity_rate(r["F_ps"], r["keep"], 1.0))
            out_levels.append(
                {
                    "id": f"d{depth}-t{n_t}",
                    "n": n,
                    "depth": depth,
                    "seed": seed,
                    "n_t": n_t,
                    "cz_layers": cz_layers(n, depth),
                    "gates": _gates(n, depth, seed),
                    "bare_key": ",".join(map(str, bare["targets"])) + "|" + bare["policy"],
                    "best_key": ",".join(map(str, best["targets"])) + "|" + best["policy"],
                    "best_beta0_key": ",".join(map(str, best_b0["targets"])) + "|" + best_b0["policy"],
                    "best_beta1_key": ",".join(map(str, best_b1["targets"])) + "|" + best_b1["policy"],
                    "configs": configs,
                }
            )
        path = out_dir / f"{prof['name']}.json"
        path.write_text(json.dumps({"profile": prof, "budget": meta["budget"], "levels": out_levels}, separators=(",", ":")))
        written.append(path)
        index["profiles"].append({"name": prof["name"], "file": path.name, "p2": prof["p2"], "p_ro": prof["p_ro"], "source": prof["source"]})
    (out_dir / "index.json").write_text(json.dumps(index, indent=1))
    written.append(out_dir / "index.json")
    return written
