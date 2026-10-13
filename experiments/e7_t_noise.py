"""E7: ablation with noisy T gates (non-virtual RZ, e.g. a magic-state budget)."""

from _common import DATA, SEEDS, slim, write_csv

from sentinels import PayloadSpec, checked_payload, evaluate_configuration, get_profile


def main():
    base = get_profile("qff-synthetic")
    rows = []
    for p_t in (0.0, 0.002, 0.01):
        prof = base.with_(p_t=p_t)
        for s in SEEDS[:3]:
            spec = PayloadSpec(6, 12, s)
            for tg in ((), (0, 2, 4)):
                cp = checked_payload(spec, tg, base)  # same checks; only T noise changes
                for t in (0, 1, 2, 4, 8, 12, 16):
                    r = evaluate_configuration(cp, t, "safe", prof)
                    r["p_t"] = p_t
                    rows.append(slim(r))
            print(p_t, s, flush=True)
    write_csv(DATA / "e7_t_noise.csv", rows)


if __name__ == "__main__":
    main()
