"""Payload circuits: the Clifford skeleton and its T-doped family.

The payload is a one-dimensional brickwork of CZ gates interleaved with random
single-qubit Cliffords drawn from {sx, s}. This is the same family used in the
IBM Quantum tutorial "Low-overhead error detection with spacetime codes", so
our numbers can be compared with that reference workflow.

T doping is described by *sites*. A site ``(k, side)`` means "a T gate on the
``side``-th qubit (0 or 1) of the ``k``-th payload CZ gate, placed immediately
after that gate". Describing sites relative to payload CZ gates, rather than
relative to instruction indices, lets us place the same T gates in circuits
that carry different sets of checks.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit

__all__ = [
    "Site",
    "PayloadSpec",
    "brickwork_clifford",
    "cz_layers",
    "all_sites",
    "site_order",
]

Site = tuple[int, int]
"""A T-gate site ``(k, side)``: after the k-th payload CZ, on its ``side`` qubit."""


@dataclass(frozen=True)
class PayloadSpec:
    """Specification of a Clifford payload.

    Attributes:
        num_qubits: Width of the payload (data qubits).
        depth: Number of brickwork CZ layers.
        seed: Seed for the random single-qubit Cliffords.
    """

    num_qubits: int = 6
    depth: int = 12
    seed: int = 7

    def build(self) -> QuantumCircuit:
        """Return the measured-free Clifford payload circuit."""
        return brickwork_clifford(self.num_qubits, self.depth, self.seed)

    @property
    def label(self) -> str:
        return f"n{self.num_qubits}-d{self.depth}-s{self.seed}"


def brickwork_clifford(num_qubits: int, depth: int, seed: int) -> QuantumCircuit:
    """Brickwork random Clifford circuit (no measurements).

    A Hadamard layer prepares |+>^n, then each of ``depth`` layers applies CZ
    on alternating nearest-neighbour pairs followed by a random choice of
    ``sx``, ``s``, ``sx`` on every qubit. Every gate is in the Clifford set
    accepted by ``qiskit_paulice.add_pauli_checks``.
    """
    if num_qubits < 2:
        raise ValueError("Need at least two qubits for a brickwork payload.")
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(num_qubits, name=f"payload_n{num_qubits}_d{depth}")
    qc.h(range(num_qubits))
    for layer in range(depth):
        for i in range(layer % 2, num_qubits - 1, 2):
            qc.cz(i, i + 1)
        for q in range(num_qubits):
            if rng.integers(0, 2):
                qc.sx(q)
            if rng.integers(0, 2):
                qc.s(q)
            if rng.integers(0, 2):
                qc.sx(q)
    return qc


def cz_layers(num_qubits: int, depth: int) -> list[list[tuple[int, int]]]:
    """The CZ pairs of every brickwork layer, in program order."""
    return [
        [(i, i + 1) for i in range(layer % 2, num_qubits - 1, 2)] for layer in range(depth)
    ]


def all_sites(num_qubits: int, depth: int) -> list[Site]:
    """Every candidate T site of the payload (two per CZ gate)."""
    n_cz = sum(len(layer) for layer in cz_layers(num_qubits, depth))
    return [(k, side) for k in range(n_cz) for side in (0, 1)]


def site_order(num_qubits: int, depth: int, seed: int) -> list[Site]:
    """A fixed random ordering of all sites.

    Both doping policies walk through this one ordering, so "blind" doping
    and "check-aware" doping start from the same candidate list and differ
    only in which sites they are allowed to use.
    """
    sites = all_sites(num_qubits, depth)
    perm = np.random.default_rng(10_000 + seed).permutation(len(sites))
    return [sites[i] for i in perm]
