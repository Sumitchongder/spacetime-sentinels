"""Shot-based execution through the Qiskit Aer ``SamplerV2`` primitive.

The exact evaluation in :mod:`sentinels.fidelity` is what the game scores use.
This module runs the *same* circuits the way an experiment would: sample
bitstrings with a primitive, compute syndromes with the post-selection map of
the checks, discard shots with a non-trivial syndrome, and compare the
surviving distribution to the ideal one. It is used to validate the exact
numbers (kept fraction and classical fidelity agree within shot noise).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import hellinger_fidelity
from qiskit_aer.primitives import SamplerV2

from .noise import NoiseProfile

__all__ = ["SampledResult", "sample_postselected"]


@dataclass
class SampledResult:
    shots: int
    kept: int
    keep: float
    keep_stderr: float
    hellinger: float
    counts_kept: dict


def _measure_map(qc: QuantumCircuit) -> dict[int, int]:
    """qubit index -> global clbit index."""
    out = {}
    for inst in qc.data:
        if inst.operation.name == "measure":
            out[qc.find_bit(inst.qubits[0]).index] = qc.find_bit(inst.clbits[0]).index
    return out


def sample_postselected(
    circuit: QuantumCircuit,
    supports: tuple[tuple[int, ...], ...],
    num_data: int,
    profile: NoiseProfile,
    ideal_probs: np.ndarray,
    shots: int = 20_000,
    seed: int = 11,
    active: tuple[bool, ...] | None = None,
) -> SampledResult:
    """Run ``circuit`` with SamplerV2 and post-select on the active checks."""
    sampler = SamplerV2(
        default_shots=shots,
        seed=seed,
        options={"backend_options": {"noise_model": profile.aer_with_readout()}},
    )
    job = sampler.run([circuit])
    data = job.result()[0].data
    # Assemble one boolean matrix (shots x num_clbits) in global clbit order.
    nclb = circuit.num_clbits
    bits = np.zeros((shots, nclb), dtype=np.uint8)
    offset = 0
    for creg in circuit.cregs:
        arr = getattr(data, creg.name).to_bool_array(order="little")
        bits[:, offset : offset + creg.size] = arr
        offset += creg.size
    mm = _measure_map(circuit)
    active = tuple(active) if active is not None else (True,) * len(supports)
    ok = np.ones(shots, dtype=bool)
    for sup, a in zip(supports, active, strict=False):
        if not a:
            continue
        par = np.zeros(shots, dtype=np.uint8)
        for q in sup:
            par ^= bits[:, mm[q]]
        ok &= par == 0
    kept = int(ok.sum())
    data_bits = np.stack([bits[ok, mm[q]] for q in range(num_data)], axis=1)
    keys = (data_bits * (1 << np.arange(num_data))).sum(axis=1)
    hist = np.bincount(keys, minlength=2**num_data)
    counts = {format(i, f"0{num_data}b"): int(c) for i, c in enumerate(hist) if c}
    ideal = {format(i, f"0{num_data}b"): float(p) for i, p in enumerate(ideal_probs) if p > 1e-12}
    keep = kept / shots
    return SampledResult(
        shots=shots,
        kept=kept,
        keep=keep,
        keep_stderr=float(np.sqrt(keep * (1 - keep) / shots)),
        hellinger=float(hellinger_fidelity(counts, ideal)) if kept else 0.0,
        counts_kept=counts,
    )
