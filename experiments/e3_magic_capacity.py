"""E3: magic capacity. How many Z-safe T sites survive as checks are added.

No simulation is needed: the Z-safe sites follow from the uncovered Paulis
reported by qiskit-paulice for every check set.
"""

from _common import DATA, DEPTHS, SEEDS, write_csv

from sentinels import PayloadSpec, checked_payload, get_profile, subsets


def main(profile_name="qff-synthetic"):
    prof = get_profile(profile_name)
    rows = []
    for d in DEPTHS + [24]:
        for s in SEEDS:
            spec = PayloadSpec(6, d, s)
            for tg in subsets(6, 6):
                cp = checked_payload(spec, tg, prof)
                total = 2 * len(cp._cz_pos)
                rows.append({"depth": d, "seed": s, "k": len(tg), "targets": list(tg),
                             "safe_sites": len(cp.zsafe_sites()), "total_sites": total, "gamma": cp.gamma})
            print(d, s, flush=True)
    write_csv(DATA / f"e3_capacity_{prof.name}.csv", rows)


if __name__ == "__main__":
    main()
