"""The exact evaluator against independent references."""

import numpy as np
from qiskit.quantum_info import DensityMatrix, Statevector

from sentinels import checked_payload, exact_evaluation, reference_state
from sentinels.experiment import choose_sites
from sentinels.fidelity import (
    _simulate_density_matrix,
    coherent_syndrome_circuit,
    stabilizer_fidelity,
)
from sentinels.sampling import sample_postselected


def test_noiseless_is_perfect(spec, profile):
    cp = checked_payload(spec, (0, 2, 4), profile)
    psi, method = reference_state(cp.bare())
    assert method == "stabilizer"
    ev = exact_evaluation(cp.circuit, cp.supports, cp.n, profile.with_(p2=0.0, p_ro=0.0), psi)
    assert abs(ev.fidelity - 1) < 1e-9 and abs(ev.keep - 1) < 1e-9


def test_aer_density_matrix_matches_quantum_info(spec, profile):
    cp = checked_payload(spec, (1, 3), profile)
    qc = coherent_syndrome_circuit(cp.circuit, cp.supports, cp.n, None)
    rho = _simulate_density_matrix(qc, profile.with_(p2=0.0, p_ro=0.0), "CPU")
    ref = DensityMatrix(Statevector(qc)).data
    assert np.abs(rho - ref).max() < 1e-10


def test_stabilizer_identity_equals_statevector_overlap(spec, profile):
    cp = checked_payload(spec, (), profile)
    bare = cp.bare()
    psi, _ = reference_state(bare)
    rho = _simulate_density_matrix(coherent_syndrome_circuit(bare, (), cp.n, profile), profile, "CPU")
    f_sv = float(np.real(np.conj(psi) @ rho @ psi))
    assert abs(stabilizer_fidelity(bare, rho) - f_sv) < 1e-10


def test_detection_raises_fidelity_and_costs_shots(spec, profile):
    cp = checked_payload(spec, (0, 1, 2, 3), profile)
    psi, _ = reference_state(cp.bare())
    ev0 = exact_evaluation(cp.bare(), (), cp.n, profile, psi)
    ev = exact_evaluation(cp.circuit, cp.supports, cp.n, profile, psi)
    assert ev.fidelity > ev0.fidelity
    assert ev.keep < 1


def test_sampler_agrees_with_exact(spec, profile):
    cp = checked_payload(spec, (0, 2, 4), profile)
    sites, _, _ = choose_sites(cp, 2, "safe")
    qc, bare = cp.doped(sites), cp.bare(sites)
    psi, method = reference_state(bare)
    assert method == "statevector"
    ev = exact_evaluation(qc, cp.supports, cp.n, profile, psi)
    sr = sample_postselected(qc, cp.supports, cp.n, profile, np.abs(psi) ** 2, shots=20000, seed=5)
    assert abs(sr.keep - ev.keep) < 5 * sr.keep_stderr + 1e-3
    assert abs(sr.hellinger - ev.hellinger) < 0.02
