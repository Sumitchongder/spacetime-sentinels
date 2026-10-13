/* Spacetime Sentinels web game.
 * Plays back results computed with Qiskit (qiskit-paulice + Qiskit Aer) for every legal move.
 * Data: docs/data/<profile>.json, written by `sentinels export`.
 */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const NS = "http://www.w3.org/2000/svg";
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
  };

  const S = {
    index: null, data: {}, profile: null, depth: 12, nT: 4, targets: new Set(), policy: "safe",
    beta: 0.5, played: null, revealBest: false, budget: 4,
  };

  // ------------------------------------------------------------------ utils
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  };
  const fmt = (x, d = 4) => (x === null || x === undefined ? "-" : Number(x).toFixed(d));
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const toast = (msg) => { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 2200); };
  const rate = (c, beta) => (c && c.feasible && c.keep > 0 ? c.F_ps * Math.pow(c.keep, beta) : 0);

  function level() {
    const d = S.data[S.profile];
    return d ? d.levels.find((l) => l.depth === S.depth && l.n_t === S.nT) : null;
  }
  function keyFor(targets, policy) {
    const t = [...targets].sort((a, b) => a - b);
    const pol = t.length === 0 || S.nT === 0 ? "none" : policy;
    return t.join(",") + "|" + pol;
  }
  function config() { const L = level(); return L ? L.configs[keyFor(S.targets, S.policy)] : null; }
  function bestFor(L, beta) {
    let best = null, br = -1;
    for (const [k, c] of Object.entries(L.configs)) {
      const r = rate(c, beta);
      if (r > br) { br = r; best = [k, c]; }
    }
    return best;
  }

  // -------------------------------------------------------------- loading
  async function load() {
    S.index = await (await fetch("data/index.json")).json();
    for (const p of S.index.profiles) S.data[p.name] = await (await fetch("data/" + p.file)).json();
    S.profile = S.index.profiles[0].name;
    S.budget = S.data[S.profile].budget;
    buildControls();
    render();
    renderBestScores();
    loadLab();
  }

  // ------------------------------------------------------------- controls
  function seg(container, values, current, label, onPick) {
    container.innerHTML = "";
    values.forEach((v) => {
      const b = document.createElement("button");
      b.textContent = label(v);
      if (v === current) b.classList.add("on");
      b.onclick = () => { onPick(v); };
      container.appendChild(b);
    });
  }
  function buildControls() {
    const levels = S.data[S.profile].levels;
    const depths = [...new Set(levels.map((l) => l.depth))].sort((a, b) => a - b);
    const ts = [...new Set(levels.map((l) => l.n_t))].sort((a, b) => a - b);
    const names = { [depths[0]]: "Shallow", [depths[1]]: "Medium", [depths[2]]: "Deep" };
    seg($("#depthSeg"), depths, S.depth, (d) => `${names[d] || ""} ${d}`.trim(), (d) => { S.depth = d; S.played = null; buildControls(); render(); });
    seg($("#tSeg"), ts, S.nT, (t) => (t === 0 ? "0 (Clifford)" : String(t)), (t) => { S.nT = t; S.played = null; buildControls(); render(); });
    const sel = $("#profileSel");
    if (!sel.options.length) {
      for (const p of S.index.profiles) {
        const o = document.createElement("option");
        o.value = p.name;
        o.textContent = p.name === "qff-synthetic" ? "QFF synthetic (p2 = 1%)" : "FakeFez calibration (Heron)";
        sel.appendChild(o);
      }
      sel.onchange = () => { S.profile = sel.value; S.played = null; render(); renderBestScores(); };
    }
    const P = S.data[S.profile].profile;
    $("#profileHint").textContent = `CZ depolarizing ${(P.p2 * 100).toFixed(2)}%, readout flip ${(P.p_ro * 100).toFixed(2)}%. Same model scores the checks and runs the circuit.`;
    $$("#policySeg button").forEach((b) => {
      b.classList.toggle("on", b.dataset.p === S.policy);
      b.disabled = S.nT === 0;
      b.onclick = () => { S.policy = b.dataset.p; S.played = null; buildControls(); render(); };
    });
    const ph = {
      safe: "T gates go only on green sites. All checks stay valid. If there are not enough green sites the move is illegal.",
      blind: "T gates go on fixed random sites. Checks hit by a T on a red site break and start firing on good shots.",
      "blind-retire": "Same blind placement, but broken checks are ignored at post-selection. Their gates are still in the circuit.",
    };
    $("#policyHint").textContent = S.nT === 0 ? "No T gates in this level: the payload is Clifford-only." : ph[S.policy];
  }

  // ---------------------------------------------------------------- board
  function renderBoard() {
    const L = level(); const c = config();
    const svg = $("#board"); svg.innerHTML = "";
    const n = L.n, D = L.depth;
    const left = 104, right = 96, top = 26, rowH = 58;
    const W = Math.max(760, left + right + D * 44), H = top + n * rowH + 30;
    const cw = (W - left - right) / D;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const y = (q) => top + q * rowH + rowH / 2;
    const xCol = (l) => left + (l + 0.5) * cw;

    // layer ticks
    for (let l = 0; l < D; l++) {
      el("text", { x: xCol(l), y: 14, "text-anchor": "middle", "font-size": 10, fill: css("--muted"), "font-family": "IBM Plex Mono" }, svg).textContent = l + 1;
    }
    // site lookup
    const flat = []; L.cz_layers.forEach((layer, li) => layer.forEach((p) => flat.push([li, p])));
    const siteXY = (s) => { const [li, p] = flat[s[0]]; return [xCol(li) + cw * 0.24, y(p[s[1]])]; };

    // wires
    for (let q = 0; q < n; q++) {
      el("line", { x1: left - 6, x2: W - right + 10, y1: y(q), y2: y(q), stroke: css("--line"), "stroke-width": 2 }, svg);
    }
    // safe / covered sites (only meaningful with checks)
    if (c && S.targets.size > 0) {
      const safe = new Set((c.safe_sites === "all" ? [] : c.safe_sites).map((s) => s.join(",")));
      for (let k = 0; k < flat.length; k++) for (const side of [0, 1]) {
        const [x, yy] = siteXY([k, side]);
        const ok = c.safe_sites === "all" || safe.has(`${k},${side}`);
        el("rect", { x: x - 6, y: yy - 6, width: 12, height: 12, rx: 3, fill: ok ? css("--good") : css("--danger"), opacity: 0.22 }, svg);
      }
    }
    // CZ gates and 1q gates
    L.cz_layers.forEach((layer, li) => {
      layer.forEach(([a, b]) => {
        el("line", { x1: xCol(li), x2: xCol(li), y1: y(a), y2: y(b), stroke: css("--cz"), "stroke-width": 2.2 }, svg);
        el("circle", { cx: xCol(li), cy: y(a), r: 4.2, fill: css("--cz") }, svg);
        el("circle", { cx: xCol(li), cy: y(b), r: 4.2, fill: css("--cz") }, svg);
      });
      for (let q = 0; q < n; q++) {
        const gs = L.gates[li][q];
        if (!gs.length) continue;
        const gx = xCol(li) + cw * 0.5;
        const g = el("rect", { x: gx - 5, y: y(q) - 5, width: 10, height: 10, rx: 2, fill: css("--panel-2"), stroke: css("--muted"), "stroke-width": 0.8, opacity: 0.8 }, svg);
        const tt = el("title", {}, g); tt.textContent = gs.map((x) => (x === "sx" ? "√X" : x.toUpperCase())).join(" · ");
      }
    });
    // checks
    const tg = [...S.targets].sort((a, b) => a - b);
    if (c && c.check_columns) {
      c.check_columns.forEach((cols, i) => {
        const q = tg[i]; if (q === undefined) return;
        const broken = (c.broken || []).includes(i);
        const col = broken ? css("--danger") : css("--accent-2");
        const xs = cols.map((l) => (l < 0 ? left - 2 : xCol(l) + cw * 0.38));
        if (xs.length > 1) el("path", { d: `M${xs[0]},${y(q) - 15} L${xs[xs.length - 1]},${y(q) - 15}`, stroke: col, "stroke-width": 1.4, "stroke-dasharray": "3 3", fill: "none", opacity: 0.8 }, svg);
        xs.forEach((x) => {
          el("line", { x1: x, x2: x, y1: y(q) - 15, y2: y(q), stroke: col, "stroke-width": 1.6 }, svg);
          el("circle", { cx: x, cy: y(q) - 15, r: 3.6, fill: col }, svg);
          el("circle", { cx: x, cy: y(q), r: 3.2, fill: "none", stroke: col, "stroke-width": 1.6 }, svg);
        });
        // syndrome support at readout
        (c.supports[i] || []).filter((s) => s < n).forEach((s) => {
          el("rect", { x: W - right + 18 + i * 14, y: y(s) - 5, width: 9, height: 10, rx: 2, fill: col, opacity: 0.85 }, svg);
        });
      });
    }
    // T gates
    if (c && c.feasible && c.sites) {
      c.sites.forEach((s) => {
        const [x, yy] = siteXY(s);
        el("path", { d: `M${x},${yy - 8} L${x + 8},${yy} L${x},${yy + 8} L${x - 8},${yy} Z`, fill: css("--magic"), stroke: "#7a5200", "stroke-width": 0.8 }, svg);
        el("text", { x, y: yy + 3.2, "text-anchor": "middle", "font-size": 8, "font-weight": 700, fill: "#3b2700" }, svg).textContent = "T";
      });
    }
    // readout boxes
    for (let q = 0; q < n; q++) {
      el("rect", { x: W - right - 2, y: y(q) - 9, width: 16, height: 18, rx: 3, fill: css("--panel-2"), stroke: css("--muted") }, svg);
      el("path", { d: `M${W - right + 1},${y(q) + 4} q5,-9 10,0`, stroke: css("--muted"), fill: "none" }, svg);
    }
    if (c && c.supports && c.supports.length) {
      el("text", { x: W - right + 18, y: H - 8, "font-size": 10, fill: css("--muted"), "font-family": "IBM Plex Mono" }, svg).textContent = "syndrome parities";
    }
    // qubit posts (clickable)
    for (let q = 0; q < n; q++) {
      const on = S.targets.has(q);
      const g = el("g", { class: "post", style: "cursor:pointer" }, svg);
      el("rect", { x: 4, y: y(q) - 15, width: 90, height: 30, rx: 15, fill: on ? css("--accent-2") : css("--panel-2"), stroke: on ? css("--accent-2") : css("--line") }, g);
      el("text", { x: 16, y: y(q) + 4.5, "font-size": 13, "font-weight": 600, fill: on ? "#06221f" : css("--text"), "font-family": "IBM Plex Mono" }, g).textContent = `q${q}`;
      el("text", { x: 44, y: y(q) + 4, "font-size": 10.5, fill: on ? "#06221f" : css("--muted") }, g).textContent = on ? "guarded" : "+ post";
      g.addEventListener("click", () => togglePost(q));
    }
  }

  function togglePost(q) {
    if (S.targets.has(q)) S.targets.delete(q);
    else {
      if (S.targets.size >= S.budget) { toast(`Ancilla budget is ${S.budget}. Remove a sentinel first.`); return; }
      S.targets.add(q);
    }
    S.played = null; render();
  }

  // ------------------------------------------------------------- pipeline
  function renderPipeline(c, played) {
    const L = level();
    $("#pl0").textContent = `${L.n} qubits · ${L.depth} CZ layers · ${S.nT} T`;
    $("#pl1").textContent = S.targets.size ? `${S.targets.size} checks · +${c ? c.added_2q : "?"} CZ` : "none";
    $("#pl2").textContent = S.targets.size ? `${S.targets.size} syndrome bits` : "no ancillas";
    $("#pl3").textContent = played && c && c.feasible ? `keep ${(c.keep * 100).toFixed(1)}% of shots` : "-";
    $$("#pipeline .stage").forEach((s, i) => s.classList.toggle("lit", !!played && (i < 1 || S.targets.size > 0)));
  }

  // --------------------------------------------------------------- pareto
  function renderPareto() {
    const L = level(); const svg = $("#pareto"); svg.innerHTML = "";
    const W = 640, H = 300, m = { l: 48, r: 14, t: 12, b: 36 };
    const pts = Object.entries(L.configs).filter(([, c]) => c.feasible && c.keep !== null);
    const fmin = Math.max(0, Math.min(...pts.map(([, c]) => c.F_ps)) - 0.05);
    const kmin = Math.max(0, Math.min(...pts.map(([, c]) => c.keep)) - 0.05);
    const X = (k) => m.l + ((k - kmin) / (1 - kmin + 1e-9)) * (W - m.l - m.r);
    const Y = (f) => H - m.b - ((f - fmin) / (1 - fmin + 1e-9)) * (H - m.t - m.b);
    // axes
    el("line", { x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b, stroke: css("--line") }, svg);
    el("line", { x1: m.l, x2: m.l, y1: m.t, y2: H - m.b, stroke: css("--line") }, svg);
    for (let i = 0; i <= 4; i++) {
      const k = kmin + (i / 4) * (1 - kmin), f = fmin + (i / 4) * (1 - fmin);
      el("text", { x: X(k), y: H - m.b + 15, "text-anchor": "middle", "font-size": 10, fill: css("--muted") }, svg).textContent = k.toFixed(2);
      el("text", { x: m.l - 6, y: Y(f) + 3, "text-anchor": "end", "font-size": 10, fill: css("--muted") }, svg).textContent = f.toFixed(2);
    }
    el("text", { x: (W + m.l) / 2, y: H - 4, "text-anchor": "middle", "font-size": 11, fill: css("--muted") }, svg).textContent = "kept-shot fraction";
    el("text", { x: 12, y: H / 2, transform: `rotate(-90 12 ${H / 2})`, "text-anchor": "middle", "font-size": 11, fill: css("--muted") }, svg).textContent = "post-selected fidelity";
    // iso-rate curves
    const best = bestFor(L, S.beta);
    const rBest = rate(best[1], S.beta);
    [0.8, 0.9, 1.0].forEach((frac) => {
      const R = rBest * frac; let d = "";
      for (let i = 0; i <= 60; i++) {
        const k = kmin + (i / 60) * (1 - kmin); const f = R / Math.pow(Math.max(k, 1e-6), S.beta);
        if (f > 1.02 || f < fmin) continue;
        d += (d ? "L" : "M") + X(k).toFixed(1) + "," + Y(f).toFixed(1);
      }
      if (d) el("path", { d, fill: "none", stroke: css("--accent"), "stroke-dasharray": frac === 1 ? "" : "4 4", opacity: frac === 1 ? 0.7 : 0.35 }, svg);
    });
    // points
    const colOf = (key) => (key.endsWith("|blind") ? css("--danger") : key.endsWith("|blind-retire") ? "#b07cff" : key.startsWith("|") ? css("--text") : css("--accent-2"));
    pts.forEach(([key, c]) => {
      el("circle", { cx: X(c.keep), cy: Y(c.F_ps), r: 3.2, fill: colOf(key), opacity: 0.55 }, svg);
    });
    // legend
    [["safe / Clifford", css("--accent-2")], ["blind", css("--danger")], ["blind + retire", "#b07cff"], ["no checks", css("--text")]].forEach(([t, col], i) => {
      el("circle", { cx: m.l + 14 + i * 130, cy: m.t + 6, r: 4, fill: col }, svg);
      el("text", { x: m.l + 22 + i * 130, y: m.t + 10, "font-size": 11, fill: css("--muted") }, svg).textContent = t;
    });
    const c = config();
    if (S.played && c && c.feasible) {
      el("circle", { cx: X(c.keep), cy: Y(c.F_ps), r: 9, fill: "none", stroke: css("--text"), "stroke-width": 2 }, svg);
    }
    if (S.revealBest || S.played) {
      const [, bc] = best; const x = X(bc.keep), yy = Y(bc.F_ps);
      let d = ""; for (let i = 0; i < 10; i++) { const r = i % 2 ? 4 : 10, a = (Math.PI / 5) * i - Math.PI / 2; d += (i ? "L" : "M") + (x + r * Math.cos(a)).toFixed(1) + "," + (yy + r * Math.sin(a)).toFixed(1); }
      el("path", { d: d + "Z", fill: css("--magic"), stroke: "#7a5200" }, svg);
    }
  }

  // --------------------------------------------------------------- result
  function renderResult() {
    const L = level(); const c = config();
    const bare = L.configs[L.bare_key];
    const best = bestFor(L, S.beta);
    const played = S.played;
    const setBar = (id, v) => { $(id).style.width = played && v !== null ? `${Math.max(0, Math.min(1, v)) * 100}%` : "0"; };
    $("#mF0").textContent = played && c ? fmt(c.F0) : "-";
    $("#mF").textContent = played && c ? fmt(c.F_ps) : "-";
    $("#mK").textContent = played && c ? fmt(c.keep) : "-";
    setBar("#bF0", c && c.F0); setBar("#bF", c && c.F_ps); setBar("#bK", c && c.keep);
    $("#cA").textContent = c ? c.ancillas : "-";
    $("#c2").textContent = c ? `+${c.added_2q}` : "-";
    $("#cD").textContent = c ? `${c.depth_2q_bare} → ${c.depth_2q}` : "-";
    $("#cS").textContent = c ? (S.targets.size ? c.n_safe_sites : "all") : "-";
    $("#cB").textContent = c ? (c.broken && c.broken.length ? c.broken.map((i) => "q" + [...S.targets].sort((a, b) => a - b)[i]).join(", ") : "none") : "-";
    const v = $("#verdict");
    if (!played || !c) {
      $("#scoreBig").textContent = "----"; $("#stars").textContent = "☆☆☆";
      $("#scoreSub").textContent = "Press Run to evaluate your move."; v.style.display = "none"; return;
    }
    if (!c.feasible) {
      $("#scoreBig").textContent = "0"; $("#stars").textContent = "☆☆☆";
      $("#scoreSub").textContent = "Illegal move";
      v.style.display = "block"; v.className = "verdict bad";
      v.textContent = `Only ${c.n_safe_sites} Z-safe sites remain for ${S.nT} T gates. Your checks cover too much spacetime: drop a sentinel, or accept blind placement.`;
      return;
    }
    const r = rate(c, S.beta), r0 = rate(bare, S.beta), rb = rate(best[1], S.beta);
    const stars = (r > r0 * 1.0005 ? 1 : 0) + (r >= 0.98 * rb ? 1 : 0) + (r >= 0.999 * rb ? 1 : 0);
    const nstar = Math.max(stars, r >= 0.999 * rb ? 3 : stars);
    $("#scoreBig").textContent = Math.round(1000 * r);
    $("#stars").textContent = "★".repeat(nstar) + "☆".repeat(3 - nstar);
    $("#scoreSub").textContent = `R = F·keep^${S.beta.toFixed(2)} = ${r.toFixed(4)} · unprotected ${r0.toFixed(4)} · best ${rb.toFixed(4)}`;
    v.style.display = "block";
    let msg; let bad = false;
    if (c.broken && c.broken.length && S.policy === "blind") { msg = `A T gate landed on an X/Y wire of ${c.broken.length} check(s). Broken checks fire even on perfect shots, so you threw away good data.`; bad = true; }
    else if (c.broken && c.broken.length && S.policy === "blind-retire") { msg = "You retired the broken checks, but their gates are still entangled with the data. Ignoring a broken check does not undo the damage it does to the state."; bad = true; }
    else if (r < r0) { msg = "The checks cost more than they caught. At this depth the noise added by the check gates outweighs the errors they detect."; bad = true; }
    else if (nstar === 3) msg = "Optimal. No legal move in this level has a higher fidelity rate at this shot price.";
    else msg = `Better than no protection. The optimum for this shot price uses checks on ${best[0].split("|")[0] ? "q" + best[0].split("|")[0].split(",").join(", q") : "no qubits"}.`;
    v.className = "verdict" + (bad ? " bad" : ""); v.textContent = msg;
  }

  function renderPills() {
    const L = level(); const P = S.data[S.profile].profile;
    $("#statusPills").innerHTML = `<span class="pill">level <b>${L.id}</b></span><span class="pill">legal moves <b>${Object.keys(L.configs).length}</b></span><span class="pill">noise <b>${P.name}</b></span><span class="pill">engine <b>Qiskit Aer</b></span>`;
    const used = S.targets.size;
    $("#budget").innerHTML = Array.from({ length: S.budget }, (_, i) => `<span class="${i < used ? "used" : ""}"></span>`).join("");
    $("#budgetTxt").textContent = `${used} of ${S.budget} ancillas in use`;
  }

  function render() {
    if (!level()) return;
    renderPills(); renderBoard(); renderPipeline(config(), S.played); renderPareto(); renderResult();
  }

  // --------------------------------------------------------------- actions
  function run() {
    const c = config();
    if (!c) { toast("No data for this move."); return; }
    S.played = true;
    render();
    if (c.feasible) {
      const k = `best:${S.profile}:${level().id}:${S.beta.toFixed(2)}`;
      const sc = Math.round(1000 * rate(c, S.beta));
      if (sc > store.get(k, -1)) { store.set(k, sc); toast("New personal best for this level"); }
      renderBestScores();
    }
  }
  function revealBest() {
    const L = level(); const [key] = bestFor(L, S.beta);
    const [t, pol] = key.split("|");
    S.targets = new Set(t ? t.split(",").map(Number) : []);
    if (pol !== "none") S.policy = pol;
    S.revealBest = true; S.played = true; buildControls(); render();
    toast("Showing the optimal move for this shot price");
  }
  function renderBestScores() {
    const d = S.data[S.profile]; if (!d) return;
    const rows = d.levels.map((L) => [L.id, store.get(`best:${S.profile}:${L.id}:0.50`, null)]).filter(([, v]) => v !== null);
    $("#bestScores").innerHTML = rows.length ? rows.map(([id, v]) => `<div class="metric"><span class="k">${id}</span><span class="v">${v}</span></div>`).join("") : "Play a level to start your record. Stored only in this browser.";
  }

  // ------------------------------------------------------------------ lab
  async function loadLab() {
    try {
      const s = await (await fetch("data/summary.json")).json();
      $("#kpis").innerHTML = s.kpis.map((k) => `<div class="kpi"><b>${k.value}</b><span>${k.label}</span></div>`).join("");
      $("#figs").innerHTML = s.figures.map((f) => `<figure><img loading="lazy" src="assets/figures/${f.file}" alt="${f.title}"><figcaption><b>${f.title}.</b> ${f.caption}</figcaption></figure>`).join("");
      $("#buildInfo").textContent = s.build || "";
    } catch (e) { $("#figs").innerHTML = '<p class="hint">Run make figures to populate this page.</p>'; }
  }

  // ------------------------------------------------------------------ init
  function initChrome() {
    $$(".tab").forEach((t) => t.addEventListener("click", () => {
      $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
      $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + t.dataset.view));
      if (t.dataset.view === "play") render();
    }));
    const th = store.get("theme", null) || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    document.documentElement.dataset.theme = th;
    $("#theme").onclick = () => {
      const nt = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = nt; store.set("theme", nt); render();
    };
    $("#beta").oninput = (e) => { S.beta = Number(e.target.value); $("#betaVal").textContent = S.beta.toFixed(2); render(); };
    $("#runBtn").onclick = run;
    $("#bestBtn").onclick = revealBest;
    $("#clearBtn").onclick = () => { S.targets.clear(); S.played = null; render(); };
    $("#randBtn").onclick = () => {
      S.targets.clear(); const k = Math.floor(Math.random() * (S.budget + 1));
      while (S.targets.size < k) S.targets.add(Math.floor(Math.random() * level().n));
      S.policy = ["safe", "blind", "blind-retire"][Math.floor(Math.random() * 3)];
      S.played = null; buildControls(); render();
    };
    $("#shareBtn").onclick = async () => {
      const c = config(); if (!c || !S.played) { toast("Run a move first"); return; }
      const txt = `Spacetime Sentinels ${level().id} (${S.profile}): posts [${[...S.targets].sort().join(",")}] ${S.policy}, F_ps=${fmt(c.F_ps)} keep=${fmt(c.keep)} score ${Math.round(1000 * rate(c, S.beta))}`;
      try { await navigator.clipboard.writeText(txt); toast("Copied"); } catch (e) { toast(txt); }
    };
    // repository links derived from the GitHub Pages URL
    const m = location.hostname.match(/^([^.]+)\.github\.io$/);
    const repo = m ? `https://github.com/${m[1]}/${location.pathname.split("/").filter(Boolean)[0] || "spacetime-sentinels"}` : "https://github.com/";
    $("#repoLink").href = repo;
    $("#reportLink").href = repo + "/blob/main/report/main.pdf";
    $("#videoLink").href = repo + "#video-walkthrough";
  }

  initChrome();
  load().catch((e) => { console.error(e); toast("Could not load game data"); });
})();
