"""Make every figure of the report and the web 'Lab' page from results/data.

Usage: python experiments/make_figures.py
"""

from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from _common import DATA, FIG, ROOT

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 220, "font.size": 9, "axes.titlesize": 9.5,
    "axes.labelsize": 9, "legend.fontsize": 7.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "font.family": "DejaVu Sans",
})
C = {"none": "#6b7280", "clifford": "#111827", "safe": "#0f9f8f", "blind": "#d6264b", "blind-retire": "#7c3aed"}
DC = {6: "#93c5fd", 12: "#3b82f6", 18: "#1e3a8a", 24: "#0b1d4d"}
LBL = {"none": "no checks", "safe": "safe-zone T", "blind": "blind T", "blind-retire": "blind T + retire", "clifford": "Clifford"}


def read(name):
    p = DATA / name
    if not p.exists():
        print("missing", p)
        return []
    with open(p) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in list(r.items()):
            if v in ("", "None"):
                r[k] = None
                continue
            try:
                r[k] = json.loads(v)
            except Exception:
                pass
    return rows


def save(fig, name):
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print("figure", name)


def agg(rows, xkey, ykey, filt):
    g = defaultdict(list)
    for r in rows:
        if filt(r) and r.get(ykey) is not None:
            g[r[xkey]].append(r[ykey])
    xs = sorted(g)
    return np.array(xs), np.array([np.mean(g[x]) for x in xs]), np.array([np.std(g[x]) for x in xs])


# --------------------------------------------------------------------------- E1
def fig_check_count(summary):
    rows = read("e1_check_count_qff-synthetic.csv")
    if not rows:
        return
    for r in rows:
        r["gain"] = r["R"] / r["F0"]
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.4))
    for d in (6, 12, 18):
        def f(r, d=d):
            return r["depth"] == d
        for a, key, lab in zip(ax, ("F_ps", "keep", "gain"), ("post-selected fidelity $F_{ps}$", "kept fraction", "rate gain $R_{1/2}/F_0$"), strict=False):
            x, m, s = agg(rows, "k", key, f)
            a.errorbar(x, m, yerr=s, marker="o", ms=3, lw=1.3, capsize=2, color=DC[d], label=f"depth {d}")
            a.set_xlabel("number of checks $k$")
            a.set_ylabel(lab)
    ax[2].axhline(1, color="k", lw=0.8, ls=":")
    ax[0].legend(frameon=False)
    save(fig, "fig_check_count")
    for d in (12, 18):
        x, m, s = agg(rows, "k", "gain", lambda r, d=d: r["depth"] == d)
        summary[f"best_gain_d{d}"] = (int(x[np.argmax(m)]), float(m.max()))
    x, m, s = agg(rows, "k", "gain", lambda r: r["depth"] == 6)
    summary["gain_d6"] = list(map(float, m))


# --------------------------------------------------------------------------- E2
def fig_t_count(summary):
    rows = read("e2_t_count_qff-synthetic.csv")
    if not rows:
        return
    fig, ax = plt.subplots(2, 3, figsize=(7.2, 4.3), sharex=True)
    for col, d in enumerate((6, 12, 18)):
        for pol in ("none", "safe", "blind", "blind-retire"):
            def f(r, pol=pol, d=d):
                if r["depth"] != d or not r["feasible"]:
                    return False
                if pol == "none":
                    return r["policy"] == "none"
                return r["targets"] == [0, 2, 4] and (r["policy"] == pol or (r["n_t"] == 0 and r["policy"] == "clifford"))
            x, m, s = agg(rows, "n_t", "F_ps", f)
            ax[0, col].errorbar(x, m, yerr=s, marker="o", ms=2.8, lw=1.2, capsize=2, color=C[pol], label=LBL[pol])
            x, m, s = agg(rows, "n_t", "keep", f)
            ax[1, col].errorbar(x, m, yerr=s, marker="o", ms=2.8, lw=1.2, capsize=2, color=C[pol])
        ax[0, col].set_title(f"depth {d}, checks on q0, q2, q4")
        ax[1, col].set_xlabel("number of T gates")
    ax[0, 0].set_ylabel("$F_{ps}$ (or $F_0$)")
    ax[1, 0].set_ylabel("kept fraction")
    ax[0, 0].legend(frameon=False)
    save(fig, "fig_t_count")
    # numbers for the text
    def mean(pol, d, t, tg=(0, 2, 4), key="F_ps"):
        v = [r[key] for r in rows if r["depth"] == d and r["n_t"] == t and r["policy"] == pol and r["feasible"]
             and (pol == "none" or r["targets"] == list(tg))]
        v = [x for x in v if x is not None]
        return float(np.mean(v)) if v else None
    summary["t_count"] = {
        f"d{d}": {pol: {t: [mean(pol, d, t), mean(pol, d, t, key="keep")] for t in (0, 1, 2, 4, 8, 16)}
                  for pol in ("none", "safe", "blind", "blind-retire", "clifford")}
        for d in (6, 12, 18)
    }


# --------------------------------------------------------------------------- E3
def fig_capacity(summary):
    rows = read("e3_capacity_qff-synthetic.csv")
    if not rows:
        return
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.5))
    for d in (6, 12, 18, 24):
        x, m, s = agg(rows, "k", "safe_sites", lambda r, d=d: r["depth"] == d)
        ax[0].errorbar(x, m, yerr=s, marker="o", ms=3, capsize=2, color=DC[d], label=f"depth {d}")
        tot = [r["total_sites"] for r in rows if r["depth"] == d][0]
        ax[1].errorbar(x, m / tot, yerr=s / tot, marker="o", ms=3, capsize=2, color=DC[d])
    for t in (4, 8, 16):
        ax[0].axhline(t, color="#c98a00", lw=0.8, ls="--")
        ax[0].text(6.05, t, f"{t} T", va="center", fontsize=7, color="#c98a00")
    ax[0].set_xlabel("number of checks $k$")
    ax[0].set_ylabel("Z-safe T sites")
    ax[0].set_yscale("log")
    ax[1].set_xlabel("number of checks $k$")
    ax[1].set_ylabel("fraction of sites that are Z-safe")
    ax[0].legend(frameon=False, ncol=2)
    save(fig, "fig_capacity")
    for d in (6, 12, 18, 24):
        x, m, s = agg(rows, "k", "safe_sites", lambda r, d=d: r["depth"] == d)
        tot = [r["total_sites"] for r in rows if r["depth"] == d][0]
        summary[f"capacity_d{d}"] = {"total": tot, "by_k": [float(v) for v in m]}


# ------------------------------------------------------------------ E4 (grid)
def load_grid(name):
    p = DATA / f"grid_{name}.json"
    return json.loads(p.read_text())["records"] if p.exists() else []


def fig_grid(summary):
    recs = load_grid("qff-synthetic")
    if not recs:
        return
    def rate(r, b):
        return r["F_ps"] * r["keep"] ** b
    feas = [r for r in recs if r["feasible"] and r["F_ps"] is not None]
    # Pareto for one level
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
    d, t = 18, 4
    lv = [r for r in feas if r["depth"] == d and r["n_t"] == t]
    for pol in ("blind-retire", "blind", "safe", "none"):
        pts = [r for r in lv if r["policy"] == pol]
        ax[0].scatter([r["keep"] for r in pts], [r["F_ps"] for r in pts], s=10, alpha=0.7, color=C[pol], label=LBL[pol])
    best = max(lv, key=lambda r: rate(r, 0.5))
    ax[0].scatter([best["keep"]], [best["F_ps"]], marker="*", s=140, color="#f59e0b", edgecolor="k", zorder=5, label="best $R_{1/2}$")
    kk = np.linspace(0.2, 1, 100)
    for f in (0.8, 0.9, 1.0):
        ax[0].plot(kk, f * rate(best, 0.5) / np.sqrt(kk), color="#2563eb", lw=0.8, ls="-" if f == 1 else ":")
    ax[0].set_ylim(0.3, 1.0)
    ax[0].set_xlabel("kept fraction")
    ax[0].set_ylabel("$F_{ps}$")
    ax[0].set_title(f"every legal move, depth {d}, {t} T gates")
    ax[0].legend(frameon=False, loc="lower left")
    # winner k vs beta
    betas = np.linspace(0, 1, 21)
    for d in (6, 12, 18):
        for t in (0, 16):
            lv = [r for r in feas if r["depth"] == d and r["n_t"] == t]
            ks = [max(lv, key=lambda r, b=b: rate(r, b))["k"] for b in betas]
            ax[1].plot(betas, ks, marker="o" if t == 0 else "s", ms=2.5, lw=1.2, color=DC[d], ls="-" if t == 0 else "--",
                       label=f"depth {d}, {t} T")
    ax[1].set_xlabel(r"shot price $\beta$")
    ax[1].set_ylabel("checks in the winning move")
    ax[1].legend(frameon=False, fontsize=6.5)
    save(fig, "fig_pareto_beta")

    # best move table per level
    table = []
    for d in (6, 12, 18):
        for t in sorted({r["n_t"] for r in feas}):
            lv = [r for r in recs if r["depth"] == d and r["n_t"] == t]
            fl = [r for r in lv if r["feasible"]]
            b = max(fl, key=lambda r: rate(r, 0.5))
            bare = next(r for r in lv if r["k"] == 0)
            n_inf = sum(1 for r in lv if not r["feasible"])
            table.append({"depth": d, "n_t": t, "targets": b["targets"], "policy": b["policy"], "F0": bare["F0"],
                          "F_ps": b["F_ps"], "keep": b["keep"], "R": rate(b, 0.5), "gain": rate(b, 0.5) / bare["F0"],
                          "infeasible_moves": n_inf, "moves": len(lv)})
    (DATA / "best_moves_qff-synthetic.json").write_text(json.dumps(table, indent=1))
    summary["best_moves"] = table

    # check location: spread of R over target sets of equal size
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    pos = 0
    ticks, labels = [], []
    for d in (6, 12, 18):
        for k in (1, 2, 3, 4):
            v = [rate(r, 0.5) / r["F0"] for r in feas if r["depth"] == d and r["n_t"] == 0 and r["k"] == k]
            ax.boxplot([v], positions=[pos], widths=0.6, patch_artist=True,
                       boxprops={"facecolor": DC[d], "alpha": 0.6}, medianprops={"color": "k"}, showfliers=True)
            ticks.append(pos)
            labels.append(f"d{d}\nk={k}")
            pos += 1
        pos += 0.6
    ax.axhline(1, color="k", lw=0.8, ls=":")
    ax.set_xticks(ticks, labels, fontsize=7)
    ax.set_ylabel("$R_{1/2}/F_0$")
    ax.set_title("same number of checks, different target qubits (Clifford payload)")
    save(fig, "fig_location")
    spread = {}
    for d in (6, 12, 18):
        v = [rate(r, 0.5) / r["F0"] for r in feas if r["depth"] == d and r["n_t"] == 0 and r["k"] == 2]
        spread[d] = [min(v), max(v)]
    summary["location_spread_k2"] = spread

    # fake-fez vs synthetic
    fez = load_grid("fake-fez")
    if fez:
        ff = [r for r in fez if r["feasible"] and r["F_ps"] is not None]
        fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.4))
        for a, data, name in ((ax[0], feas, "QFF synthetic ($p_2$=1%)"), (ax[1], ff, "FakeFez calibration")):
            for d in (6, 12, 18):
                ks = range(0, 5)
                m = []
                for k in ks:
                    v = [rate(r, 0.5) / r["F0"] for r in data if r["depth"] == d and r["n_t"] == 0 and r["k"] == k]
                    m.append(max(v))
                a.plot(list(ks), m, marker="o", ms=3, color=DC[d], label=f"depth {d}")
            a.axhline(1, color="k", lw=0.8, ls=":")
            a.set_title(name)
            a.set_xlabel("checks $k$ (best target set)")
            a.set_ylabel("best $R_{1/2}/F_0$")
        ax[0].legend(frameon=False)
        save(fig, "fig_profiles")


# --------------------------------------------------------------------------- E5
def fig_noise(summary):
    rows = read("e5_noise_sweep.csv")
    if not rows:
        return
    for r in rows:
        r["gain"] = r["R"] / r["F0"]
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    for d in (6, 12, 18):
        for k, ls in ((2, ":"), (4, "-")):
            x, m, s = agg(rows, "p2", "gain", lambda r, d=d, k=k: r["depth"] == d and r["k"] == k)
            ax.errorbar(x, m, yerr=s, marker="o", ms=2.8, capsize=2, color=DC[d], ls=ls, label=f"d{d}, k={k}")
    ax.axhline(1, color="k", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("two-qubit error $p_2$ (= readout error)")
    ax.set_ylabel("$R_{1/2}/F_0$")
    ax.legend(frameon=False, ncol=2, fontsize=6.5)
    save(fig, "fig_noise")
    summary["noise"] = {f"d{d}k{k}": list(map(float, agg(rows, "p2", "gain", lambda r, d=d, k=k: r["depth"] == d and r["k"] == k)[1]))
                        for d in (6, 12, 18) for k in (2, 4)}


# --------------------------------------------------------------------------- E6
def fig_validation(summary):
    rows = read("e6_validation.csv")
    if not rows:
        return
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.5))
    for prof, mk in (("qff-synthetic", "o"), ("fake-fez", "s")):
        rr = [r for r in rows if r["profile"] == prof]
        ax[0].errorbar([r["keep_exact"] for r in rr], [r["keep_sampled"] for r in rr], yerr=[2 * r["keep_stderr"] for r in rr],
                       fmt=mk, ms=4, capsize=2, label=prof)
        ax[1].plot([r["H_exact"] for r in rr], [r["H_sampled"] for r in rr], mk, ms=4, label=prof)
    for a in ax:
        lo, hi = a.get_xlim()
        a.plot([0, 1], [0, 1], "k:", lw=0.8)
        a.set_xlim(lo, hi)
        a.set_ylim(lo, hi)
    ax[0].set_xlabel("kept fraction, exact (density matrix)")
    ax[0].set_ylabel("kept fraction, SamplerV2 50k shots")
    ax[1].set_xlabel("classical fidelity, exact")
    ax[1].set_ylabel("classical fidelity, sampled")
    ax[0].legend(frameon=False)
    save(fig, "fig_validation")
    dk = [abs(r["keep_exact"] - r["keep_sampled"]) / max(r["keep_stderr"], 1e-9) for r in rows]
    dh = [abs(r["H_exact"] - r["H_sampled"]) for r in rows]
    di = [abs(r["F0_overlap"] - r["F0_stabilizer_identity"]) for r in rows if r.get("F0_stabilizer_identity") is not None]
    summary["validation"] = {"max_keep_sigma": float(max(dk)), "max_H_diff": float(max(dh)),
                             "max_stabilizer_identity_diff": float(max(di)) if di else None, "cases": len(rows)}


# --------------------------------------------------------------------------- E7
def fig_t_noise(summary):
    rows = read("e7_t_noise.csv")
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    cols = {0.0: "#0f9f8f", 0.002: "#f59e0b", 0.01: "#d6264b"}
    for pt in (0.0, 0.002, 0.01):
        for tg, ls, key in (([], ":", "F0"), ([0, 2, 4], "-", "F_ps")):
            x, m, s = agg(rows, "n_t", key, lambda r, pt=pt, tg=tg: abs(r["p_t"] - pt) < 1e-12 and r["targets"] == tg)
            ax.errorbar(x, m, yerr=s, marker="o", ms=2.5, capsize=2, color=cols[pt], ls=ls,
                        label=f"$p_T$={pt}, " + ("no checks" if not tg else "3 checks"))
    ax.set_xlabel("number of T gates (safe zones)")
    ax.set_ylabel("fidelity")
    ax.legend(frameon=False, fontsize=6.3, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    save(fig, "fig_t_noise")


def web_summary(summary):
    out = ROOT / "docs" / "assets" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    figs = [
        ("fig_t_count", "T count against check placement", "Post-selected fidelity and kept fraction versus T count for three doping policies with checks on q0, q2 and q4. Safe-zone doping keeps both flat; blind doping collapses both."),
        ("fig_capacity", "Magic capacity", "Number of Z-safe sites where a T gate keeps every check valid, versus number of checks. Dashed lines mark T demands of 4, 8 and 16."),
        ("fig_check_count", "How many checks?", "Fidelity, kept fraction and fidelity-rate gain versus the number of qiskit-paulice checks. Shallow circuits do not benefit."),
        ("fig_pareto_beta", "Trade-off and shot price", "Left: every legal move of one level. Right: the number of checks in the winning move as the shot price changes."),
        ("fig_noise", "When does detection pay?", "Fidelity-rate gain versus two-qubit error rate."),
        ("fig_location", "Check location matters", "Spread of the gain over different target qubits with the same number of checks."),
        ("fig_profiles", "Two noise models", "Best gain per number of checks for the synthetic model and the FakeFez calibration."),
        ("fig_validation", "Validation", "Exact density-matrix numbers against 50,000-shot SamplerV2 runs."),
        ("fig_t_noise", "If T gates were noisy", "Ablation: depolarizing noise on T gates makes T count lower the raw fidelity too."),
    ]
    got = []
    for name, title, cap in figs:
        src = FIG / f"{name}.png"
        if src.exists():
            shutil.copy(src, out / src.name)
            got.append({"file": src.name, "title": title, "caption": cap})
    kpis = []
    tc = summary.get("t_count", {}).get("d18", {})
    if tc:
        s16 = tc["safe"].get(16) or tc["safe"].get("16")
        b16 = tc["blind"].get(16) or tc["blind"].get("16")
        if s16 and s16[0] and b16 and b16[0]:
            kpis.append({"value": f"{s16[0]:.2f} vs {b16[0]:.2f}", "label": "F_ps with 16 T gates at depth 18: safe-zone vs blind doping"})
    if "best_gain_d18" in summary:
        k, g = summary["best_gain_d18"]
        kpis.append({"value": f"×{g:.2f}", "label": f"best fidelity-rate gain at depth 18 ({k} checks)"})
    cap = summary.get("capacity_d18")
    if cap:
        kpis.append({"value": f"{cap['by_k'][0]:.0f} → {cap['by_k'][4]:.0f}", "label": "Z-safe T sites at depth 18 with 0 and 4 checks"})
    v = summary.get("validation")
    if v:
        kpis.append({"value": f"{v['max_keep_sigma']:.1f}σ", "label": "largest exact-vs-sampled kept-fraction deviation"})
    from datetime import date
    (ROOT / "docs" / "data" / "summary.json").write_text(json.dumps({"kpis": kpis, "figures": got, "build": f"data built {date.today()}"}, indent=1))


def main():
    summary = {}
    for f in (fig_check_count, fig_t_count, fig_capacity, fig_grid, fig_noise, fig_validation, fig_t_noise):
        try:
            f(summary)
        except Exception as e:  # keep going so one missing dataset does not block the rest
            print("FAILED", f.__name__, repr(e))
            raise
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    web_summary(summary)
    for p in FIG.glob("*.pdf"):
        shutil.copy(p, ROOT / "report" / "figures" / p.name)


if __name__ == "__main__":
    main()
