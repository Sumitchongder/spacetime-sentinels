"""Physics invariants of the checks and of T doping."""

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from sentinels import checked_payload, noiseless_false_alarms
from sentinels.experiment import choose_sites


def test_bare_circuit_matches_payload(spec, profile):
    cp = checked_payload(spec, (0, 2, 4), profile)
    bare = cp.bare()
    assert np.allclose(Statevector(bare).probabilities(), Statevector(spec.build()).probabilities())


def test_clifford_checks_never_fire_without_noise(spec, profile):
    cp = checked_payload(spec, (0, 1, 2, 3), profile)
    assert max(noiseless_false_alarms(cp.circuit, cp.supports, cp.n)) < 1e-12


@pytest.mark.parametrize("n_t", [1, 2, 4])
def test_safe_doping_keeps_every_check_valid(spec, profile, n_t):
    """T on a Z-safe site commutes with every check: no false alarms."""
    cp = checked_payload(spec, (0, 2, 4), profile)
    sites, feasible, _ = choose_sites(cp, n_t, "safe")
    assert feasible
    fa = noiseless_false_alarms(cp.doped(sites), cp.supports, cp.n)
    assert max(fa) < 1e-12


def test_blind_doping_can_break_checks(spec, profile):
    cp = checked_payload(spec, (0, 1, 2, 3), profile)
    unsafe = [s for s in sorted({(k, s) for k in range(len(cp._cz_pos)) for s in (0, 1)}) if s not in cp.zsafe_sites()]
    assert unsafe, "with four checks some sites must be X/Y-covered"
    fa = noiseless_false_alarms(cp.doped(unsafe[:1]), cp.supports, cp.n)
    assert max(fa) > 1e-6


def test_more_checks_fewer_safe_sites(spec, profile):
    caps = [len(checked_payload(spec, t, profile).zsafe_sites()) for t in [(), (0,), (0, 2), (0, 2, 4)]]
    assert caps[0] >= caps[1] >= caps[3]
