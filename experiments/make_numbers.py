"""Write report/numbers.tex: every number quoted in the report, straight from results/data.

Keeping numbers in generated macros means the text can never drift from the data.
"""

from __future__ import annotations

import csv
import json

import numpy as np
from _common import DATA, ROOT


def rows(name):
    with open(DATA / name) as fh:
        out = list(csv.DictReader(fh))
    for r in out:
        for k, v in r.items():
            try:
                r[k] = json.loads(v) if v not in ("", "None") else None
            except Exception:
                pass
    return out


def grid(name):
    return json.loads((DATA / f"grid_{name}.json").read_text())


def m(vals):
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else float("nan")


def main():
    N = {}
    def f3(x):
        return f"{x:.3f}"
    def pct(x):
        return f"{100 * x:.0f}\\%"

    g = grid("qff-synthetic")
    gf = grid("fake-fez")
    recs = g["records"]
    N["NumMoves"] = f"{len(recs) + len(gf['records']):,}".replace(",", "{,}")
    N["NumMovesPerProfile"] = f"{len(recs):,}".replace(",", "{,}")
    N["GridMinutes"] = f"{max(g['meta']['wall_seconds'], gf['meta']['wall_seconds']) / 60:.0f}"
    N["PtwoFez"] = f"{gf['meta']['profile']['p2']:.4f}"
    N["ProFez"] = f"{gf['meta']['profile']['p_ro']:.4f}"
    bare = {r["depth"]: r for r in recs if r["k"] == 0 and r["n_t"] == 0}
    N["FzeroShallow"], N["FzeroMedium"], N["FzeroDeep"] = (f3(bare[d]["F0"]) for d in (6, 12, 18))
    N["HzeroDeep"] = f3(bare[18]["H0"])
    n_illegal = sum(1 for r in recs if not r["feasible"])
    N["NumIllegal"] = str(n_illegal)

    # E1: check count (5 seeds)
    e1 = rows("e1_check_count_qff-synthetic.csv")
    for d, name in ((6, "Shallow"), (12, "Medium"), (18, "Deep")):
        by_k = {k: [r for r in e1 if r["depth"] == d and r["k"] == k] for k in range(7)}
        gains = {k: m([r["R"] / r["F0"] for r in v]) for k, v in by_k.items() if v}
        kbest = max(gains, key=gains.get)
        N[f"EoneGain{name}"] = f3(gains[kbest])
        N[f"EoneK{name}"] = str(kbest)
        N[f"EoneFps{name}"] = f3(m([r["F_ps"] for r in by_k[kbest]]))
        N[f"EoneKeep{name}"] = f3(m([r["keep"] for r in by_k[kbest]]))
        N[f"EoneFzero{name}"] = f3(m([r["F0"] for r in by_k[0]]))
        N[f"EoneGainOne{name}"] = f3(gains[1])
        N[f"EoneFpsSix{name}"] = f3(m([r["F_ps"] for r in by_k[6]]))
        N[f"EoneKeepSix{name}"] = f3(m([r["keep"] for r in by_k[6]]))
        N[f"EoneGammaZero{name}"] = f3(m([r["gamma"] for r in by_k[1]]))

    # E2: T count
    e2 = rows("e2_t_count_qff-synthetic.csv")

    def e2m(d, pol, t, key, tg=(0, 2, 4)):
        return m([r[key] for r in e2 if r["depth"] == d and r["n_t"] == t and r["policy"] == pol and r["feasible"]
                  and (pol == "none" or r["targets"] == list(tg))])

    for d, name in ((12, "Medium"), (18, "Deep")):
        N[f"EtwoCliff{name}"] = f3(e2m(d, "clifford", 0, "F_ps"))
        N[f"EtwoCliffKeep{name}"] = f3(e2m(d, "clifford", 0, "keep"))
        for t in (4, 16):
            for pol, pn in (("safe", "Safe"), ("blind", "Blind"), ("blind-retire", "Retire"), ("none", "None")):
                key = "F_ps" if pol != "none" else "F0"
                N[f"Etwo{pn}F{name}T{'Four' if t == 4 else 'Sixteen'}"] = f3(e2m(d, pol, t, key))
                N[f"Etwo{pn}K{name}T{'Four' if t == 4 else 'Sixteen'}"] = f3(e2m(d, pol, t, "keep") if pol != "none" else 1.0)
        nb = [len(r["broken"]) for r in e2 if r["depth"] == d and r["policy"] == "blind" and r["n_t"] == 4 and r["targets"] == [0, 2, 4]]
        N[f"EtwoBrokenFour{name}"] = f"{np.mean(nb):.1f}"
        N[f"EtwoNoneFzeroTSixteen{name}"] = f3(e2m(d, "none", 16, "F0"))
        N[f"EtwoNoneFzeroTZero{name}"] = f3(e2m(d, "none", 0, "F0"))
    # safe-T fidelity drift (harmless -> harmful)
    drift = []
    for d in (6, 12, 18):
        a, b = e2m(d, "clifford", 0, "F_ps"), e2m(d, "safe", 16, "F_ps")
        if not np.isnan(b):
            drift.append(a - b)
    N["EtwoSafeDrift"] = f"{max(drift):.3f}" if drift else "n/a"

    # E3 capacity
    e3 = rows("e3_capacity_qff-synthetic.csv")
    for d, name in ((6, "Shallow"), (12, "Medium"), (18, "Deep"), (24, "Huge")):
        tot = [r["total_sites"] for r in e3 if r["depth"] == d][0]
        N[f"CapTotal{name}"] = str(tot)
        for k, kn in ((0, "Zero"), (1, "One"), (2, "Two"), (4, "Four"), (6, "Six")):
            v = [r["safe_sites"] for r in e3 if r["depth"] == d and r["k"] == k]
            N[f"Cap{name}{kn}"] = f"{np.mean(v):.1f}"
            N[f"CapMin{name}{kn}"] = str(int(np.min(v)))
            N[f"CapFrac{name}{kn}"] = pct(np.mean(v) / tot)

    # best moves from the grid
    best = json.loads((DATA / "best_moves_qff-synthetic.json").read_text())
    for r in best:
        key = f"Best{ {6: 'Shallow', 12: 'Medium', 18: 'Deep'}[r['depth']] }T{r['n_t']}".replace(" ", "")
        key = key.replace("T0", "TZero").replace("T16", "TSixteen").replace("T1", "TOne").replace("T2", "TTwo").replace("T4", "TFour").replace("T8", "TEight")
        N[key + "Targets"] = ",".join(f"q{t}" for t in r["targets"]) or "none"
        N[key + "Policy"] = r["policy"]
        N[key + "Gain"] = f3(r["gain"])
        N[key + "Fps"] = f3(r["F_ps"])
        N[key + "Keep"] = f3(r["keep"])
        N[key + "Fzero"] = f3(r["F0"])
        N[key + "Illegal"] = str(r["infeasible_moves"])

    rows_tex = []
    for r in best:
        tg = ",".join(str(t) for t in r["targets"]) or "none"
        pol = {"none": "Clifford" if r["n_t"] == 0 else "", "safe": "safe", "blind": "blind", "blind-retire": "retire"}[r["policy"]]
        label = f"$q_{{{tg}}}$" if r["targets"] else "none"
        rows_tex.append(f"{r['depth']} & {r['n_t']} & {label}{', ' + pol if pol and r['targets'] else ''} & {r['F0']:.3f} & {r['F_ps']:.3f} ({r['keep']:.3f}) & {r['gain']:.3f}")
    N["BestTableRows"] = " \\\\ ".join(rows_tex)
    loc = json.loads((DATA / "summary.json").read_text()).get("location_spread_k2", {})
    if loc:
        N["LocMinDeep"], N["LocMaxDeep"] = f3(loc["18"][0]), f3(loc["18"][1])
        N["LocMinShallow"], N["LocMaxShallow"] = f3(loc["6"][0]), f3(loc["6"][1])

    # validation
    v = json.loads((DATA / "summary.json").read_text()).get("validation", {})
    N["ValKeepSigma"] = f"{v.get('max_keep_sigma', float('nan')):.1f}"
    N["ValHdiff"] = f"{v.get('max_H_diff', float('nan')):.3f}"
    N["ValStabDiff"] = f"{(v.get('max_stabilizer_identity_diff') or 0):.0e}"

    # E5 noise sweep: break-even
    e5 = rows("e5_noise_sweep.csv")
    for d, name in ((6, "Shallow"), (12, "Medium"), (18, "Deep")):
        for p in (0.001, 0.01, 0.03):
            pn = {0.001: "Low", 0.01: "Mid", 0.03: "High"}[p]
            vv = [r["R"] / r["F0"] for r in e5 if r["depth"] == d and r["k"] == 4 and abs(r["p2"] - p) < 1e-12]
            N[f"EfiveGain{name}{pn}"] = f3(m(vv))

    # E7 T noise
    e7 = rows("e7_t_noise.csv")
    for pt, pn in ((0.0, "Zero"), (0.01, "High")):
        for key, kn in (("F0", "Fzero"), ("F_ps", "Fps")):
            tg = [] if key == "F0" else [0, 2, 4]
            for t, tn in ((0, "TZero"), (16, "TSixteen")):
                vv = [r[key] for r in e7 if abs(r["p_t"] - pt) < 1e-12 and r["n_t"] == t and r["targets"] == tg and r["feasible"]]
                N[f"Eseven{kn}{pn}{tn}"] = f3(m(vv))

    # fake-fez headline
    fr = gf["records"]
    for d, name in ((6, "Shallow"), (12, "Medium"), (18, "Deep")):
        lv = [r for r in fr if r["depth"] == d and r["n_t"] == 0 and r["feasible"]]
        b = max(lv, key=lambda r: r["R"])
        N[f"FezGain{name}"] = f3(b["R"] / b["F0"])
        N[f"FezK{name}"] = str(b["k"])
        N[f"FezFzero{name}"] = f3(b["F0"])

    lines = ["% Auto-generated by experiments/make_numbers.py. Do not edit by hand."]
    for k, val in sorted(N.items()):
        lines.append(f"\\newcommand{{\\{k}}}{{{val}}}")
    (ROOT / "report" / "numbers.tex").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(N)} macros")
    for k, val in sorted(N.items()):
        print(f"{k:40s} {val}")


if __name__ == "__main__":
    main()
