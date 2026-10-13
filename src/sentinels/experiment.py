"""Evaluate game configurations and sweep the full decision space.

A *configuration* is one complete set of player decisions for a level:

* which data qubits carry a check (the ancilla budget is spent here),
* how many T gates the payload carries (the level's "magic quota"),
* how the T gates are placed:

  ``safe``          only on Z-safe sites, so every check stays valid;
  ``blind``         on the first sites of a fixed random order, ignoring the
                    checks, and post-selecting on every check (broken ones too);
  ``blind-retire``  same placement, but checks broken by T gates are retired
                    (their syndrome is ignored, their gates and noise remain).

Every number stored in a record comes from Qiskit: check placement from
qiskit-paulice, states from qiskit.quantum_info, noisy evolution from Qiskit
Aer. Nothing is hand-set.
"""

from __future__ import annotations

import itertools
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict

import numpy as np

from .checks import CheckedPayload, checked_payload
from .fidelity import (
    exact_evaluation,
    noiseless_false_alarms,
    reference_state,
    stabilizer_fidelity,
)
from .noise import NoiseProfile
from .payloads import PayloadSpec, site_order
from .scoring import fidelity_rate

__all__ = ["POLICIES", "evaluate_configuration", "evaluate_targets", "run_grid", "subsets"]

POLICIES = ("safe", "blind", "blind-retire")
_FA_TOL = 1e-9


def subsets(num_qubits: int, budget: int) -> list[tuple[int, ...]]:
    """All target sets with at most ``budget`` checks."""
    out: list[tuple[int, ...]] = []
    for k in range(budget + 1):
        out.extend(itertools.combinations(range(num_qubits), k))
    return out


def choose_sites(cp: CheckedPayload, n_t: int, policy: str) -> tuple[list, bool, int]:
    """T sites for a policy. Returns (sites, feasible, number_of_safe_sites)."""
    order = site_order(cp.n, cp.spec.depth, cp.spec.seed)
    safe = cp.zsafe_sites()
    if policy == "safe":
        chosen = [s for s in order if s in safe][:n_t]
        return chosen, len(chosen) == n_t, len(safe)
    return order[:n_t], True, len(safe)


def evaluate_configuration(
    cp: CheckedPayload,
    n_t: int,
    policy: str,
    profile: NoiseProfile,
    device: str = "CPU",
    with_dfe: bool = False,
) -> dict:
    """Evaluate one configuration and return a flat record."""
    t0 = time.perf_counter()
    sites, feasible, n_safe = choose_sites(cp, n_t, policy)
    rec = {
        "n": cp.n,
        "depth": cp.spec.depth,
        "payload_seed": cp.spec.seed,
        "profile": profile.name,
        "p2": profile.p2,
        "p_ro": profile.p_ro,
        "p_t": profile.p_t,
        "targets": list(cp.targets),
        "k": len(cp.targets),
        "n_t": n_t,
        "policy": policy if cp.targets else "none",
        "feasible": feasible,
        "n_safe_sites": n_safe,
        "n_sites_total": 2 * len(cp._cz_pos),
        "sites": [list(s) for s in sites],
        "supports": [list(s) for s in cp.supports],
        "ancilla_qubits": list(cp.ancillas),
        "check_columns": cp.check_gate_columns(),
        "safe_sites": sorted([list(s) for s in cp.zsafe_sites()]) if cp.targets else "all",
        "gamma": cp.gamma,
        **cp.cost(),
    }
    if not feasible:
        rec.update({"F0": None, "F_ps": None, "keep": None, "R": None, "gain": None})
        return rec

    checked = cp.doped(sites)
    bare = cp.bare(sites)
    psi, ref_method = reference_state(bare)
    rec["reference"] = ref_method

    fa = noiseless_false_alarms(checked, cp.supports, cp.n)
    broken = [i for i, p in enumerate(fa) if p > _FA_TOL]
    rec["false_alarm"] = [round(x, 6) for x in fa]
    rec["broken"] = broken
    active = tuple(i not in broken for i in range(len(cp.supports)))
    if policy != "blind-retire":
        active = (True,) * len(cp.supports)
    rec["active"] = [bool(a) for a in active]

    ev0 = exact_evaluation(bare, (), cp.n, profile, psi, device=device)
    ev = exact_evaluation(checked, cp.supports, cp.n, profile, psi, active=active, device=device)
    rec.update(
        {
            "F0": ev0.fidelity,
            "H0": ev0.hellinger,
            "F_ps": ev.fidelity,
            "H_ps": ev.hellinger,
            "keep": ev.keep,
            "R": fidelity_rate(ev.fidelity, ev.keep, 0.5),
            "R_beta0": ev.fidelity,
            "R_beta1": ev.fidelity * ev.keep,
            "gain": fidelity_rate(ev.fidelity, ev.keep, 0.5) / ev0.fidelity,
        }
    )
    if with_dfe and ref_method == "stabilizer":
        # Cross-check: the stabilizer-group (DFE) identity gives the same F0.
        from .fidelity import _simulate_density_matrix, coherent_syndrome_circuit

        rho0 = _simulate_density_matrix(coherent_syndrome_circuit(bare, (), cp.n, profile), profile, device)
        rec["F0_stabilizer_identity"] = stabilizer_fidelity(bare, rho0)
    rec["seconds"] = round(time.perf_counter() - t0, 3)
    return rec


def evaluate_targets(args) -> list[dict]:
    """All (n_t, policy) configurations for one target set. Picklable task."""
    spec, targets, profile, t_counts, device, check_seed = args
    cp = checked_payload(spec, tuple(targets), profile, check_seed)
    out = []
    for n_t in t_counts:
        pols = ("none",) if (n_t == 0 or not targets) else POLICIES
        for pol in pols:
            out.append(evaluate_configuration(cp, n_t, "safe" if pol == "none" else pol, profile, device))
            out[-1]["policy"] = pol if targets else "none"
    return out


def run_grid(
    specs: list[PayloadSpec],
    profile: NoiseProfile,
    budget: int = 4,
    t_counts=(0, 1, 2, 4, 8),
    workers: int | None = None,
    device: str = "CPU",
    check_seed: int = 1,
    progress: bool = True,
) -> list[dict]:
    """Sweep every target subset (size <= budget) for every payload spec."""
    tasks = [
        (spec, targets, profile, tuple(t_counts), device, check_seed)
        for spec in specs
        for targets in subsets(spec.num_qubits, budget)
    ]
    # Largest subsets first so the slow tasks start early.
    tasks.sort(key=lambda t: -len(t[1]))
    workers = workers or max(1, (os.cpu_count() or 1))
    records: list[dict] = []
    t0 = time.perf_counter()
    if workers == 1:
        it = map(evaluate_targets, tasks)
        for i, recs in enumerate(it):
            records.extend(recs)
            if progress:
                print(f"[{i + 1}/{len(tasks)}] {time.perf_counter() - t0:7.1f}s", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for i, recs in enumerate(ex.map(evaluate_targets, tasks, chunksize=1)):
                records.extend(recs)
                if progress and (i + 1) % 10 == 0:
                    print(f"[{i + 1}/{len(tasks)}] {time.perf_counter() - t0:7.1f}s", flush=True)
    return records


def spec_dict(spec: PayloadSpec) -> dict:
    return asdict(spec)


def summarize(records: list[dict]) -> dict:
    feas = [r for r in records if r.get("feasible") and r.get("R") is not None]
    return {
        "configurations": len(records),
        "feasible": len(feas),
        "mean_seconds": float(np.mean([r.get("seconds", 0) for r in feas])) if feas else 0.0,
    }
