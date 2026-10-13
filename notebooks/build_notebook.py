"""Builds notebooks/01_walkthrough.ipynb (run: python notebooks/build_notebook.py)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
def md(text):
    nb.cells.append(nbf.v4.new_markdown_cell(text))


def code(text):
    nb.cells.append(nbf.v4.new_code_cell(text))

md("""# Spacetime Sentinels: reproducible walkthrough

This notebook follows the six required steps of the Qiskit Fall Fest 2026 Advanced-track challenge
(error detection with spacetime codes) and shows how every number used by the game is produced.

| Step | Section |
|---|---|
| 1. Build the payloads | §1 |
| 2. Fix the reference | §2 |
| 3. Add checks with qiskit-paulice | §3, §4 |
| 4. Run under noise | §5 |
| 5. Measure | §5, §6 |
| 6. Compare | §7 |

Runtime: about two minutes on a laptop CPU.""")
code("""import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "src"))
import numpy as np, qiskit, qiskit_aer, qiskit_paulice
from qiskit.quantum_info import Statevector, StabilizerState, Clifford
from sentinels import PayloadSpec, get_profile, checked_payload, evaluate_configuration, reference_state
from sentinels.checks import checked_prefixes
from sentinels.experiment import choose_sites
from sentinels.fidelity import exact_evaluation, noiseless_false_alarms
from sentinels.sampling import sample_postselected
from importlib.metadata import version
print("qiskit", qiskit.__version__, "| qiskit-aer", qiskit_aer.__version__, "| qiskit-paulice", version("qiskit-paulice"))""")

md("""## 1. Payloads
A 6-qubit brickwork of CZ gates with random `sx`/`s` single-qubit Cliffords (the family of the IBM tutorial).
The T-doped family inserts 0, 1, 2, 4, 8 or 16 T gates into the same skeleton.""")
code("""spec = PayloadSpec(num_qubits=6, depth=12, seed=7)
payload = spec.build()
print("width", payload.num_qubits, "| depth", payload.depth(), "| two-qubit depth",
      payload.depth(lambda i: i.operation.num_qubits == 2), "| gates", dict(payload.count_ops()))
payload.draw("text", fold=-1)""")

md("""## 2. Reference and fidelity measure
* Clifford payload: the ideal output is a stabilizer state, computed by stabilizer simulation (`StabilizerState`).
* T-doped payload: statevector simulation (`Statevector`), cheap at 6 qubits.

**Fidelity measure:** the state fidelity $F=\\langle\\psi|\\sigma|\\psi\\rangle$ between the ideal state and the
post-selected data state $\\sigma$, because it is sensitive to every error, including phase errors that a
computational-basis distance would miss, and for Clifford states it equals the stabilizer average
$2^{-n}\\sum_{G\\in S}\\mathrm{Tr}(\\sigma G)$ that direct fidelity estimation measures.""")
code("""stab = StabilizerState(Clifford(payload))
psi = Statevector(payload)
print("stabilizer generators:", stab.clifford.to_labels(mode="S"))
print("stabilizer and statevector agree:", np.allclose(Statevector(stab.clifford.to_circuit()).probabilities(), psi.probabilities()))""")

md("""## 3. Checks with qiskit-paulice
`add_pauli_checks` returns one circuit per number of checks. Each check is an ancilla that applies
controlled-Pauli gates to one target qubit at several times, then is measured; the syndrome is the
parity of the ancilla bit and some output bits (`check_support`).""")
code("""prof = get_profile("qff-synthetic")
print(prof)
variants = checked_prefixes(spec, (0, 1, 2, 3), prof)
for v in variants:
    print(f"k={len(v.targets)}  targets={v.targets}  gamma={v.gamma if v.gamma is None else round(v.gamma,4)}  supports={v.supports}")""")
code("""cp = checked_payload(spec, (0, 2, 4), prof)
cp.circuit.draw("text", fold=-1, idle_wires=False)""")

md("""## 4. T doping across checks
A hand-made or automatic check stays valid across a T gate only if it acts as I or Z on that wire, because T is diagonal.
`CheckedCircuit.uncovered_paulis` lists the wires where a Z error is invisible to every check: those are the
**Z-safe sites**. We verify validity directly: a valid check never fires on the noiseless circuit.""")
code("""safe = cp.zsafe_sites()
print(f"{len(safe)} of {2*len(cp._cz_pos)} T sites are Z-safe for checks on {cp.targets}")
for policy in ("safe", "blind"):
    sites, ok, _ = choose_sites(cp, 4, policy)
    fa = noiseless_false_alarms(cp.doped(sites), cp.supports, cp.n)
    print(f"{policy:6s} sites={sites}  false-alarm rate per check on the IDEAL circuit = {np.round(fa, 4)}")""")

md("""## 5. Run under noise and measure
The noise model is the one announced in the challenge text (`NoiseModel(gate_noise=0.01)`, plus 1% readout),
applied identically by qiskit-paulice (to score checks) and by Qiskit Aer (to simulate). Every configuration
records the fidelity without checks, the post-selected fidelity, the kept fraction and the added cost.""")
code("""rows = []
for targets in [(), (0, 2, 4), (0, 1, 2, 3)]:
    c = checked_payload(spec, targets, prof)
    for n_t, pol in [(0, "safe"), (4, "safe"), (4, "blind"), (4, "blind-retire")]:
        if not targets and pol != "safe":
            continue
        r = evaluate_configuration(c, n_t, pol, prof)
        rows.append(r)
        print(f"checks={str(targets):12s} T={n_t} {pol:12s} F0={r['F0']:.4f}  F_ps={r['F_ps']:.4f}  keep={r['keep']:.4f}  "
              f"R={r['R']:.4f}  ancillas={r['ancillas']} +2q={r['added_2q']} depth2q={r['depth_2q_bare']}->{r['depth_2q']} broken={r['broken']}")""")

md("""## 6. Validation with the SamplerV2 primitive
The game uses exact density-matrix numbers. The same circuits sampled with the Aer `SamplerV2` primitive give the same
kept fraction and classical fidelity within shot noise.""")
code("""sites, _, _ = choose_sites(cp, 4, "safe")
qc, bare = cp.doped(sites), cp.bare(sites)
psi_t, method = reference_state(bare)
ev = exact_evaluation(qc, cp.supports, cp.n, prof, psi_t)
sr = sample_postselected(qc, cp.supports, cp.n, prof, np.abs(psi_t)**2, shots=30_000)
print(f"reference: {method}")
print(f"kept fraction exact {ev.keep:.4f} | sampled {sr.keep:.4f} ± {sr.keep_stderr:.4f}")
print(f"classical fidelity exact {ev.hellinger:.4f} | sampled {sr.hellinger:.4f}")""")

md("""## 7. Compare: the best trade-off
The full sweep over every legal move (`experiments/e0_game_grid.py`) is summarised in `results/data/best_moves_qff-synthetic.json`.""")
code("""import json, pathlib
p = pathlib.Path("../results/data/best_moves_qff-synthetic.json")
if p.exists():
    for r in json.loads(p.read_text()):
        print(f"depth {r['depth']:2d}  T {r['n_t']:2d}  best checks {str(r['targets']):14s} {r['policy']:12s} "
              f"F0 {r['F0']:.3f} -> F_ps {r['F_ps']:.3f} keep {r['keep']:.3f}  gain x{r['gain']:.3f}  illegal moves {r['infeasible_moves']}")
else:
    print("Run `make grid figures` first.")""")
md("""## 8. Play a round live
`sentinels play` runs the same computation live in the terminal. The web game at GitHub Pages plays back these
pre-computed Qiskit results for every legal move.""")
code("""from sentinels.cli import main
main(["play", "--depth", "12", "--t", "4", "--targets", "0,2,4", "--policy", "safe"])""")
nbf.write(nb, "notebooks/01_walkthrough.ipynb")
print("ok")
