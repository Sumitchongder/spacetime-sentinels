"""Command-line interface: ``sentinels <command>``.

Commands
--------
play       Play one round in the terminal. The round is evaluated live with
           qiskit-paulice and Qiskit Aer (nothing is looked up).
evaluate   Evaluate one configuration and print the full record as JSON.
grid       Sweep the whole decision space (same as experiments/e0_game_grid.py).
export     Convert grid results to the JSON used by the web game.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checks import checked_payload
from .experiment import POLICIES, evaluate_configuration, run_grid
from .noise import get_profile
from .payloads import PayloadSpec
from .scoring import fidelity_rate


def _parse_targets(text: str) -> tuple[int, ...]:
    text = text.strip()
    if not text or text.lower() == "none":
        return ()
    return tuple(sorted({int(t) for t in text.replace(" ", "").split(",") if t}))


def _fmt(rec: dict) -> str:
    if not rec["feasible"]:
        return (
            f"  Infeasible: only {rec['n_safe_sites']} Z-safe sites for {rec['n_t']} T gates.\n"
            "  Drop a check or use blind placement."
        )
    lines = [
        f"  ancillas {rec['ancillas']}   extra 2q gates {rec['added_2q']}   "
        f"2q depth {rec['depth_2q_bare']} -> {rec['depth_2q']}",
        f"  fidelity without checks   F0   = {rec['F0']:.4f}",
        f"  post-selected fidelity    F_ps = {rec['F_ps']:.4f}",
        f"  kept-shot fraction        keep = {rec['keep']:.4f}",
        f"  fidelity rate R = F_ps*sqrt(keep) = {rec['R']:.4f}   (bare {rec['F0']:.4f}, gain x{rec['gain']:.3f})",
    ]
    if rec.get("broken"):
        lines.append(f"  checks broken by T gates: {rec['broken']}  (false-alarm rates {rec['false_alarm']})")
    return "\n".join(lines)


def cmd_play(args) -> int:
    prof = get_profile(args.profile)
    spec = PayloadSpec(args.n, args.depth, args.seed)
    print(f"\nSPACETIME SENTINELS  |  {spec.num_qubits} data qubits, {spec.depth} CZ layers, "
          f"{args.t} T gates  |  noise {prof.name} (p2={prof.p2:.4g}, p_ro={prof.p_ro:.4g})")
    print(f"Ancilla budget: {args.budget}. Choose data qubits 0..{spec.num_qubits - 1} to guard.")
    targets = _parse_targets(input("Sentinel posts (e.g. 0,2,4 or none): ") if args.targets is None else args.targets)
    if len(targets) > args.budget:
        print("Over budget.")
        return 1
    policy = args.policy
    if policy is None and args.t > 0 and targets:
        policy = input(f"Magic placement {POLICIES}: ").strip() or "safe"
    policy = policy or "safe"
    print("\nRunning qiskit-paulice + Qiskit Aer (exact density matrix)...")
    cp = checked_payload(spec, targets, prof)
    rec = evaluate_configuration(cp, args.t, policy, prof)
    bare = evaluate_configuration(checked_payload(spec, (), prof), args.t, "safe", prof)
    print(_fmt(rec))
    if rec["feasible"]:
        score = round(1000 * rec["R"])
        print(f"\n  SCORE {score}   (unprotected circuit scores {round(1000 * bare['R'])})")
    return 0


def cmd_evaluate(args) -> int:
    prof = get_profile(args.profile)
    spec = PayloadSpec(args.n, args.depth, args.seed)
    cp = checked_payload(spec, _parse_targets(args.targets), prof)
    rec = evaluate_configuration(cp, args.t, args.policy, prof, device=args.device)
    if rec.get("R") is not None:
        rec["R_beta"] = fidelity_rate(rec["F_ps"], rec["keep"], args.beta)
    json.dump(rec, sys.stdout, indent=1)
    print()
    return 0


def cmd_grid(args) -> int:
    prof = get_profile(args.profile)
    specs = [PayloadSpec(args.n, d, args.seed) for d in args.depths]
    recs = run_grid(specs, prof, args.budget, args.t_counts, args.workers, args.device)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    meta = {"profile": prof.__dict__, "specs": [s.__dict__ for s in specs], "budget": args.budget,
            "t_counts": args.t_counts}
    Path(args.out).write_text(json.dumps({"meta": meta, "records": recs}))
    print(f"wrote {len(recs)} records to {args.out}")
    return 0


def cmd_export(args) -> int:
    from .export import export_web

    for p in export_web([Path(f) for f in args.grids], Path(args.out)):
        print("wrote", p)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sentinels", description="Spacetime Sentinels: a game of error detection with spacetime codes")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--profile", default="qff-synthetic", help="qff-synthetic | fake-fez")
        p.add_argument("--n", type=int, default=6)
        p.add_argument("--depth", type=int, default=12)
        p.add_argument("--seed", type=int, default=7)

    p = sub.add_parser("play", help="play one round live in the terminal")
    common(p)
    p.add_argument("--t", type=int, default=4, help="number of T gates")
    p.add_argument("--budget", type=int, default=4)
    p.add_argument("--targets", default=None)
    p.add_argument("--policy", default=None, choices=POLICIES)
    p.set_defaults(func=cmd_play)

    p = sub.add_parser("evaluate", help="evaluate one configuration (JSON)")
    common(p)
    p.add_argument("--targets", default="0,2,4")
    p.add_argument("--t", type=int, default=0)
    p.add_argument("--policy", default="safe", choices=POLICIES)
    p.add_argument("--beta", type=float, default=0.5)
    p.add_argument("--device", default="CPU", choices=["CPU", "GPU"])
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("grid", help="sweep the full decision space")
    p.add_argument("--profile", default="qff-synthetic")
    p.add_argument("--n", type=int, default=6)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--depths", type=int, nargs="+", default=[6, 12, 18])
    p.add_argument("--budget", type=int, default=4)
    p.add_argument("--t-counts", type=int, nargs="+", default=[0, 1, 2, 4, 8, 16])
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--device", default="CPU", choices=["CPU", "GPU"])
    p.add_argument("--out", default="results/data/grid.json")
    p.set_defaults(func=cmd_grid)

    p = sub.add_parser("export", help="export grid results for the web game")
    p.add_argument("grids", nargs="+")
    p.add_argument("--out", default="docs/data")
    p.set_defaults(func=cmd_export)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
