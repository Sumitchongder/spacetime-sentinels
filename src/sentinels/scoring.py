"""Scoring: turning (fidelity, kept fraction) into one number, honestly.

A post-selected fidelity means nothing without its kept fraction. We combine
the two into the *fidelity rate*

    R_beta = F_ps * keep^beta.

The default ``beta = 1/2`` has a direct operational meaning. Suppose the
residual (undetected) error is depolarizing-like, so an expectation value is
damped by F_ps, and suppose we keep ``keep * N`` of ``N`` shots. The
signal-to-noise ratio of the estimate is then proportional to
``F_ps * sqrt(keep * N)``, so ``R_{1/2}`` is the signal-to-noise per square root
of a raw shot. Equivalently ``1 / R_{1/2}^2`` is the total sampling overhead
when detection is followed by a rescaling-type mitigation step, which is the
detection-then-mitigation workflow suggested in the qiskit-paulice docs.

``beta = 0`` rewards purity only (keep shots at any price) and ``beta = 1``
rewards raw yield. The game exposes beta as the "shot price" so the player can
see the optimum move.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

__all__ = ["fidelity_rate", "stars", "pareto_front", "best_record"]


def fidelity_rate(fidelity: float, keep: float, beta: float = 0.5) -> float:
    """R_beta = F * keep^beta."""
    if keep <= 0:
        return 0.0
    return float(fidelity * keep**beta)


def stars(rate: float, bare_rate: float, best_rate: float) -> int:
    """0 to 3 stars.

    1 star: beats the unprotected circuit. 2 stars: within 2% of the best
    configuration of the level. 3 stars: matches the best (within 0.1%).
    """
    s = 0
    if rate > bare_rate * 1.0005:
        s = 1
    if best_rate > 0 and rate >= 0.98 * best_rate:
        s = max(s, 2)
    if best_rate > 0 and rate >= 0.999 * best_rate:
        s = 3
    return s


def pareto_front(points: Iterable[tuple[float, float]]) -> list[int]:
    """Indices of points not dominated in (keep, fidelity), both maximised."""
    pts = list(points)
    idx = []
    for i, (k1, f1) in enumerate(pts):
        dominated = False
        for j, (k2, f2) in enumerate(pts):
            if j != i and k2 >= k1 and f2 >= f1 and (k2 > k1 or f2 > f1):
                dominated = True
                break
        if not dominated:
            idx.append(i)
    return sorted(idx, key=lambda i: pts[i][0])


def best_record(records: list[dict], beta: float = 0.5) -> dict | None:
    """Feasible record with the highest fidelity rate."""
    feas = [r for r in records if r.get("feasible", True)]
    if not feas:
        return None
    rates = np.array([fidelity_rate(r["F_ps"], r["keep"], beta) for r in feas])
    return feas[int(np.argmax(rates))]
