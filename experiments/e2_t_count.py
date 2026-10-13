"""E2: T count versus check placement.

Fixed check sets, T count swept, three doping policies, three depths, five seeds.
"""

from _common import DATA, DEPTHS, SEEDS, slim, write_csv

from sentinels import POLICIES, PayloadSpec, checked_payload, evaluate_configuration, get_profile

T_COUNTS = [0, 1, 2, 4, 8, 12, 16]
TARGET_SETS = [(0, 2, 4), (0, 1, 2, 3)]


def main(profile_name="qff-synthetic"):
    prof = get_profile(profile_name)
    rows = []
    for d in DEPTHS:
        for s in SEEDS:
            spec = PayloadSpec(6, d, s)
            bare_cp = checked_payload(spec, (), prof)
            for t in T_COUNTS:
                r = evaluate_configuration(bare_cp, t, "safe", prof)
                r["policy"] = "none"
                rows.append(slim(r))
            for tg in TARGET_SETS:
                cp = checked_payload(spec, tg, prof)
                for t in T_COUNTS:
                    for pol in POLICIES if t else ("safe",):
                        r = evaluate_configuration(cp, t, pol, prof)
                        if not t:
                            r["policy"] = "clifford"
                        rows.append(slim(r))
                print(d, s, tg, flush=True)
    write_csv(DATA / f"e2_t_count_{prof.name}.csv", rows)


if __name__ == "__main__":
    main()
