"""Exact post-selected fidelities computed with Qiskit Aer.

Reference state
---------------
For a Clifford payload the ideal output is a stabilizer state. We obtain it
with stabilizer simulation (``qiskit.quantum_info.StabilizerState``) and
evaluate the fidelity with the stabilizer-group identity

    F = <psi| sigma |psi> = 2^{-n} sum_{G in S} Tr(sigma G),

which is the quantity direct fidelity estimation targets. For T-doped payloads
the output is no longer a stabilizer state, so the reference is the
statevector (``qiskit.quantum_info.Statevector``). Both routes are cross-checked
in the test suite.

Post-selected state
-------------------
Each check produces one syndrome bit, the XOR of its ancilla bit and of some
data bits measured at the end (the "support" reported by qiskit-paulice). In
an experiment that XOR is classical post-processing. In simulation we perform
the same XOR coherently with noiseless CNOTs from the data qubits onto the
ancilla, after the readout bit-flip channel. Because these CNOTs are diagonal
on the data and act after all noise, every Z-basis statistic is identical to
the experiment, and the ancilla register ends up holding the syndrome. We then
condition on the all-zero syndrome, trace the ancillas out, and obtain the
data state ``sigma`` the sampler draws from. The two numbers reported are

    kept fraction  p_keep = Pr[syndrome = 0]
    fidelity       F_ps   = <psi| sigma |psi>.

The evaluation is exact (Aer density-matrix method, no shot noise), which
makes small differences between game moves meaningful. :mod:`sentinels.sampling`
reproduces the same numbers with finite shots through the Aer ``SamplerV2``
primitive.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Clifford, Pauli, StabilizerState, Statevector
from qiskit_aer import AerSimulator

from .noise import NoiseProfile

__all__ = [
    "Evaluation",
    "reference_state",
    "is_clifford",
    "coherent_syndrome_circuit",
    "exact_evaluation",
    "noiseless_false_alarms",
    "stabilizer_fidelity",
]

_CLIFFORD_NAMES = {"h", "s", "sdg", "sx", "sxdg", "x", "y", "z", "cz", "cx", "cy", "swap", "id"}


def is_clifford(qc: QuantumCircuit) -> bool:
    return all(inst.operation.name in _CLIFFORD_NAMES for inst in qc.data)


def reference_state(bare: QuantumCircuit) -> tuple[np.ndarray, str]:
    """Ideal output state of the unprotected circuit.

    Returns the statevector amplitudes and the method that defined it:
    ``"stabilizer"`` for Clifford circuits and ``"statevector"`` otherwise.
    For Clifford circuits the statevector is only used as a convenient
    container; the stabilizer group from ``StabilizerState`` is the reference
    (see :func:`stabilizer_fidelity`).
    """
    psi = Statevector(bare).data
    return psi, ("stabilizer" if is_clifford(bare) else "statevector")


def stabilizer_fidelity(bare: QuantumCircuit, sigma: np.ndarray) -> float:
    """F = 2^-n sum_{G in S} Tr(sigma G) for the stabilizer state prepared by ``bare``."""
    n = bare.num_qubits
    gens = StabilizerState(Clifford(bare)).clifford.to_labels(mode="S")
    gens = [Pauli(g) for g in gens]
    total = 0.0
    for mask in range(2**n):
        g = Pauli("I" * n)
        for j in range(n):
            if (mask >> j) & 1:
                g = g.compose(gens[j])
        total += float(np.real(np.trace(sigma @ g.to_matrix())))
    return total / 2**n


def coherent_syndrome_circuit(
    circuit: QuantumCircuit,
    supports: tuple[tuple[int, ...], ...],
    num_data: int,
    profile: NoiseProfile | None,
) -> QuantumCircuit:
    """Strip measurements, add the readout channel, and XOR syndromes onto ancillas."""
    qc = circuit.remove_final_measurements(inplace=False)
    if profile is not None and profile.p_ro > 0:
        err = profile.readout_error()
        for q in range(qc.num_qubits):
            qc.append(err, [q])
    for sup in supports:
        anc = [q for q in sup if q >= num_data]
        if len(anc) != 1:
            raise ValueError(f"Check support {sup} must contain exactly one ancilla.")
        for q in sup:
            if q < num_data:
                qc.cx(q, anc[0])
    return qc


@dataclass
class Evaluation:
    """Outcome of one configuration."""

    fidelity: float  # F_ps (equals raw fidelity when no check is active)
    keep: float  # kept-shot fraction
    hellinger: float  # classical fidelity of the Z-basis output distribution

    def rate(self, beta: float = 0.5) -> float:
        return self.fidelity * self.keep**beta


def _simulate_density_matrix(qc: QuantumCircuit, profile: NoiseProfile, device: str) -> np.ndarray:
    qc = qc.copy()
    qc.save_density_matrix()
    # Gate fusion is disabled on purpose: with fusion on, noiseless density-matrix
    # runs of these circuits disagreed with Statevector by up to 3e-2 in our
    # tests (qiskit-aer 0.17.2). With fusion off the agreement is ~1e-16.
    sim = AerSimulator(
        method="density_matrix",
        noise_model=profile.aer(),
        device=device,
        fusion_enable=False,
    )
    return np.asarray(sim.run(qc).result().data()["density_matrix"])


def exact_evaluation(
    circuit: QuantumCircuit,
    supports: tuple[tuple[int, ...], ...],
    num_data: int,
    profile: NoiseProfile,
    psi: np.ndarray,
    active: tuple[bool, ...] | None = None,
    device: str = "CPU",
) -> Evaluation:
    """Exact F_ps and kept fraction of a (possibly checked) circuit.

    Args:
        circuit: Circuit on ``num_data`` data qubits followed by ancillas.
        supports: Syndrome supports (one per check).
        num_data: Number of data qubits.
        profile: Noise profile.
        psi: Ideal data state.
        active: Which checks are used for post-selection. Inactive checks keep
            their gates (and their noise) but their syndrome is ignored.
        device: ``"CPU"`` or ``"GPU"`` for Qiskit Aer.
    """
    qc = coherent_syndrome_circuit(circuit, supports, num_data, profile)
    rho = _simulate_density_matrix(qc, profile, device)
    n_all = qc.num_qubits
    n_anc = n_all - num_data
    d = 2**num_data
    if n_anc == 0:
        sigma, keep = rho, 1.0
    else:
        anc_index = {q: j for j, q in enumerate(range(num_data, n_all))}
        active = tuple(active) if active is not None else (True,) * len(supports)
        act_bits = [anc_index[[q for q in sup if q >= num_data][0]] for sup, a in zip(supports, active, strict=False) if a]
        r = rho.reshape(2**n_anc, d, 2**n_anc, d)
        a_idx = np.arange(2**n_anc)
        ok = np.ones(2**n_anc, dtype=bool)
        for b in act_bits:
            ok &= ((a_idx >> b) & 1) == 0
        sel = np.nonzero(ok)[0]
        sigma = np.einsum("aiaj->ij", r[np.ix_(sel, np.arange(d), sel, np.arange(d))])
        keep = float(np.real(np.trace(sigma)))
        sigma = sigma / keep
    fid = float(np.real(np.conj(psi) @ sigma @ psi))
    p_ideal = np.abs(psi) ** 2
    p_noisy = np.clip(np.real(np.diag(sigma)), 0, None)
    hell = float(np.sum(np.sqrt(p_ideal * p_noisy)) ** 2)
    return Evaluation(fidelity=fid, keep=keep, hellinger=hell)


def noiseless_false_alarms(
    circuit: QuantumCircuit, supports: tuple[tuple[int, ...], ...], num_data: int
) -> list[float]:
    """Probability that each check fires on the *ideal* circuit.

    A valid check never fires (0.0). A check broken by a T gate on one of its
    X- or Y-type wires fires with non-zero probability, which is how the game
    detects broken checks.
    """
    if not supports:
        return []
    qc = coherent_syndrome_circuit(circuit, supports, num_data, None)
    probs = Statevector(qc).probabilities()
    idx = np.arange(len(probs))
    out = []
    for sup in supports:
        a = [q for q in sup if q >= num_data][0]
        out.append(float(probs[((idx >> a) & 1) == 1].sum()))
    return out
