"""E6: validation of the exact evaluator.

1. Shot-based runs with the Aer SamplerV2 primitive reproduce the exact
   kept fraction and classical fidelity.
2. For Clifford payloads the stabilizer-group identity reproduces F0.
"""

import numpy as np
from _common import DATA, write_csv

from sentinels import PayloadSpec, checked_payload, evaluate_configuration, get_profile, reference_state
from sentinels.experiment import choose_sites
from sentinels.fidelity import exact_evaluation
from sentinels.sampling import sample_postselected

CASES = [
    (6, (), 0, "safe"), (12, (), 4, "safe"), (12, (0, 2, 4), 0, "safe"), (12, (0, 2, 4), 4, "safe"),
    (12, (0, 2, 4), 4, "blind"), (12, (0, 2, 4), 4, "blind-retire"), (18, (0, 1, 2, 3), 0, "safe"),
    (18, (0, 1, 2, 3), 8, "safe"), (18, (0, 1, 2, 3), 8, "blind"), (6, (1, 3, 5), 2, "safe"),
]


def main():
    rows = []
    for prof_name in ("qff-synthetic", "fake-fez"):
        prof = get_profile(prof_name)
        for d, tg, t, pol in CASES:
            cp = checked_payload(PayloadSpec(6, d, 7), tg, prof)
            sites, _, _ = choose_sites(cp, t, pol)
            qc, bare = cp.doped(sites), cp.bare(sites)
            psi, method = reference_state(bare)
            rec = evaluate_configuration(cp, t, pol, prof, with_dfe=(method == "stabilizer"))
            active = tuple(rec["active"]) if tg else None
            ev = exact_evaluation(qc, cp.supports, cp.n, prof, psi, active=active)
            sr = sample_postselected(qc, cp.supports, cp.n, prof, np.abs(psi) ** 2, shots=50_000, seed=d + t, active=active)
            rows.append({
                "profile": prof_name, "depth": d, "targets": list(tg), "n_t": t, "policy": pol, "reference": method,
                "keep_exact": ev.keep, "keep_sampled": sr.keep, "keep_stderr": sr.keep_stderr,
                "H_exact": ev.hellinger, "H_sampled": sr.hellinger,
                "F0_overlap": rec["F0"], "F0_stabilizer_identity": rec.get("F0_stabilizer_identity"),
            })
            print(rows[-1], flush=True)
    write_csv(DATA / "e6_validation.csv", rows)


if __name__ == "__main__":
    main()
