"""E1: fidelity, kept fraction and fidelity rate versus number of checks.

One ``add_pauli_checks`` call per payload returns circuits with 0..6 checks
(targets 0..5 in order). Repeated for three depths and five payload seeds.
"""

from _common import DATA, DEPTHS, SEEDS, slim, write_csv

from sentinels import PayloadSpec, evaluate_configuration, get_profile
from sentinels.checks import checked_prefixes


def main(profile_name="qff-synthetic", kmax=6):
    prof = get_profile(profile_name)
    rows = []
    for d in DEPTHS:
        for s in SEEDS:
            spec = PayloadSpec(6, d, s)
            for cp in checked_prefixes(spec, tuple(range(kmax)), prof):
                rec = evaluate_configuration(cp, 0, "safe", prof)
                rows.append(slim(rec))
                print(d, s, rec["k"], round(rec["F_ps"], 4), round(rec["keep"], 4), round(rec["R"], 4), flush=True)
    write_csv(DATA / f"e1_check_count_{prof.name}.csv", rows)


if __name__ == "__main__":
    main()
