"""Noise profiles shared by check picking (qiskit-paulice) and simulation (Qiskit Aer).

Following the official tutorial, the model that *scores* candidate checks and
the model that *simulates* the circuit are the same channel:

* every CZ gate (payload or check) is followed by a two-qubit depolarizing
  channel with probability ``p2``;
* every qubit suffers a symmetric bit flip with probability ``p_ro`` at readout;
* single-qubit Cliffords are noiseless, and T gates are noiseless by default.
  On IBM hardware ``rz`` (and therefore T) is a virtual frame change, so this
  is the physically relevant default. ``p_t > 0`` switches on an optional
  depolarizing channel on T gates for the ablation study.

Two profiles are provided. ``qff-synthetic`` is the synthetic model named in
the challenge text, ``NoiseModel(gate_noise=0.01)`` with 1% readout error.
``fake-fez`` is derived from the calibration snapshot of the ``FakeFez`` Heron
backend with ``NoiseModel.from_backend(..., uniform_gate_noise=True)``, exactly
as the tutorial derives its model from a real backend.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cache

from qiskit_aer.noise import NoiseModel as AerNoiseModel
from qiskit_aer.noise import depolarizing_error, pauli_error
from qiskit_paulice.noise_models import NoiseModel as PauliceNoiseModel

__all__ = ["NoiseProfile", "get_profile", "PROFILES"]


@dataclass(frozen=True)
class NoiseProfile:
    """A uniform Pauli noise model.

    Attributes:
        name: Profile identifier.
        p2: Two-qubit depolarizing probability after each CZ.
        p_ro: Readout bit-flip probability.
        p_t: Depolarizing probability on each T gate (0 = virtual RZ).
        source: Human-readable provenance of the numbers.
    """

    name: str
    p2: float
    p_ro: float
    p_t: float = 0.0
    source: str = ""

    def paulice(self) -> PauliceNoiseModel:
        """The model handed to ``add_pauli_checks`` for scoring checks."""
        return PauliceNoiseModel(gate_noise=self.p2, readout_noise=self.p_ro)

    def aer(self) -> AerNoiseModel | None:
        """The gate part of the model used by Qiskit Aer.

        Readout is applied separately as an explicit bit-flip channel (see
        :func:`sentinels.fidelity.readout_channel`) so that the exact
        density-matrix evaluation and the shot-based sampler see the same
        physics.
        """
        if self.p2 <= 0 and self.p_t <= 0:
            return None
        nm = AerNoiseModel()
        if self.p2 > 0:
            nm.add_all_qubit_quantum_error(depolarizing_error(self.p2, 2), ["cz"])
        if self.p_t > 0:
            nm.add_all_qubit_quantum_error(depolarizing_error(self.p_t, 1), ["t", "tdg"])
        return nm

    def aer_with_readout(self) -> AerNoiseModel:
        """Gate noise plus a readout error, for shot-based sampling."""
        from qiskit_aer.noise import ReadoutError

        nm = self.aer() or AerNoiseModel()
        if self.p_ro > 0:
            p = self.p_ro
            nm.add_all_qubit_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]))
        return nm

    def readout_error(self):
        return pauli_error([("X", self.p_ro), ("I", 1 - self.p_ro)])

    def with_(self, **kwargs) -> NoiseProfile:
        return replace(self, **kwargs)


@cache
def _fake_fez_profile() -> NoiseProfile:
    from qiskit_ibm_runtime.fake_provider import FakeFez

    model = PauliceNoiseModel.from_backend(FakeFez(), list(range(6)), uniform_gate_noise=True)
    return NoiseProfile(
        name="fake-fez",
        p2=float(model.gate_noise),
        p_ro=float(model.readout_noise),
        source="qiskit-paulice NoiseModel.from_backend(FakeFez(), layout=[0..5], uniform_gate_noise=True)",
    )


PROFILES = {
    "qff-synthetic": NoiseProfile(
        name="qff-synthetic",
        p2=0.01,
        p_ro=0.01,
        source="Challenge text: synthetic NoiseModel(gate_noise=0.01); 1% readout",
    ),
}


def get_profile(name: str, **overrides) -> NoiseProfile:
    """Look up a profile by name, optionally overriding fields."""
    if name == "fake-fez":
        prof = _fake_fez_profile()
    elif name in PROFILES:
        prof = PROFILES[name]
    else:
        raise KeyError(f"Unknown noise profile {name!r}. Known: qff-synthetic, fake-fez")
    return prof.with_(**overrides) if overrides else prof
