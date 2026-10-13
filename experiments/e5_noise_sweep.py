"""E5: when does detection pay? Gain in fidelity rate versus gate error.

Checks are re-picked for every noise level (the paulice cost depends on it).
"""

from _common import DATA, SEEDS, slim, write_csv

from sentinels import PayloadSpec, evaluate_configuration, get_profile
from sentinels.checks import checked_prefixes

P2 = [0.001, 0.002, 0.005, 0.01, 0.02, 0.03]


def main():
    base = get_profile("qff-synthetic")
    rows = []
    for p2 in P2:
        prof = base.with_(name=f"p2={p2}", p2=p2, p_ro=p2)
        for d in (6, 12, 18):
            for s in SEEDS[:3]:
                cps = checked_prefixes(PayloadSpec(6, d, s), (0, 1, 2, 3), prof)
                for cp in cps:
                    rows.append(slim(evaluate_configuration(cp, 0, "safe", prof)))
                print(p2, d, s, flush=True)
    write_csv(DATA / "e5_noise_sweep.csv", rows)


if __name__ == "__main__":
    main()
