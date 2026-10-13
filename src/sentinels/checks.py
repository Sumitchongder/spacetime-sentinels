"""Spacetime Pauli checks via qiskit-paulice, plus the T-doping rules.

The central object is :class:`CheckedPayload`: a payload circuit that has
been dressed by ``qiskit_paulice.add_pauli_checks`` with one check per chosen
target qubit. It knows

* where the payload CZ gates ended up inside the checked circuit,
* which T sites are *Z-safe*, i.e. sites where every check acts as I or Z.
  A T gate there commutes with every check, so all checks stay valid
  (this is the rule from the challenge text, and the doping rule of
  Martiel et al., "Sampling hard circuits with verifiably high fidelity"),
* how to build the doped circuit and the matching check-free circuit.

``add_pauli_checks`` only accepts Clifford circuits, so checks are always
found on the Clifford skeleton and T gates are inserted afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from qiskit import QuantumCircuit
from qiskit_paulice import add_pauli_checks

from .noise import NoiseProfile
from .payloads import PayloadSpec, Site, cz_layers

__all__ = ["CheckedPayload", "checked_payload", "checked_prefixes", "strip_checks", "two_qubit_depth"]


def strip_checks(qc: QuantumCircuit, num_data: int) -> QuantumCircuit:
    """Remove every check gate and ancilla, keeping the data-qubit gates.

    qiskit-paulice implements a controlled-X or controlled-Y check as a CZ
    sandwiched by single-qubit basis changes on the target. Those basis
    changes are merged into neighbouring data gates, so deleting the CZ
    leaves gates that compose to the identity around it. The result is the
    unprotected circuit that the checked circuit is protecting.
    """
    out = QuantumCircuit(num_data, global_phase=qc.global_phase, name=f"{qc.name}_bare")
    for inst in qc.data:
        if inst.operation.name in ("measure", "barrier"):
            continue
        idx = [qc.find_bit(q).index for q in inst.qubits]
        if any(i >= num_data for i in idx):
            continue
        out.append(inst.operation, idx)
    return out


def two_qubit_depth(qc: QuantumCircuit) -> int:
    return qc.depth(lambda inst: inst.operation.num_qubits == 2)


def _data_cz_positions(qc: QuantumCircuit, num_data: int) -> list[int]:
    return [
        i
        for i, inst in enumerate(qc.data)
        if inst.operation.num_qubits == 2
        and all(qc.find_bit(q).index < num_data for q in inst.qubits)
    ]


@dataclass
class CheckedPayload:
    """A payload circuit carrying spacetime Pauli checks.

    Attributes:
        spec: Payload specification.
        targets: Data qubits that carry a check (one ancilla each).
        circuit: Checked circuit returned by qiskit-paulice (with measurements).
        supports: For every check, the qubits (data and its ancilla) whose
            measured bits XOR to that check's syndrome.
        ancillas: Ancilla qubit index of every check.
        gamma: qiskit-paulice ``gamma`` cost of the check set.
    """

    spec: PayloadSpec
    targets: tuple[int, ...]
    circuit: QuantumCircuit
    supports: tuple[tuple[int, ...], ...]
    ancillas: tuple[int, ...]
    gamma: float | None
    _cz_pos: list[int] = field(default_factory=list, repr=False)

    @property
    def n(self) -> int:
        return self.spec.num_qubits

    def __post_init__(self) -> None:
        # qiskit-paulice re-synthesises the circuit and may reorder commuting
        # CZ gates, so payload CZ number k is matched by its position along
        # each of its two wires (the order of gates on a wire is preserved).
        positions = _data_cz_positions(self.circuit, self.n)
        per_wire: dict[int, list[int]] = {q: [] for q in range(self.n)}
        for i in positions:
            for q in self.circuit.data[i].qubits:
                per_wire[self.circuit.find_bit(q).index].append(i)
        count = {q: 0 for q in range(self.n)}
        mapped = []
        for layer in cz_layers(self.n, self.spec.depth):
            for a, b in layer:
                ia, ib = per_wire[a][count[a]], per_wire[b][count[b]]
                if ia != ib:
                    raise RuntimeError("Could not match payload CZ gates inside the checked circuit.")
                count[a] += 1
                count[b] += 1
                mapped.append(ia)
        if len(mapped) != len(positions):
            raise RuntimeError("Checked circuit has an unexpected number of data CZ gates.")
        self._cz_pos = mapped

    # ------------------------------------------------------------------ sites
    def site_location(self, site: Site) -> tuple[int, int]:
        """Instruction index and qubit of a T site inside the checked circuit."""
        k, side = site
        inst = self.circuit.data[self._cz_pos[k]]
        qubit = sorted(self.circuit.find_bit(q).index for q in inst.qubits)[side]
        return self._cz_pos[k], qubit

    def zsafe_sites(self) -> set[Site]:
        """Sites where a Z error is invisible to every check, so T keeps all checks valid."""
        if not self.supports:
            return {(k, s) for k in range(len(self._cz_pos)) for s in (0, 1)}
        loc_to_site = {}
        for k in range(len(self._cz_pos)):
            for side in (0, 1):
                loc_to_site[self.site_location((k, side))] = (k, side)
        out = set()
        for unc in self.checked_object.uncovered_paulis:
            if unc.pauli != "Z" or unc.after_instruction is None:
                continue
            key = (unc.after_instruction, unc.qubit)
            if key in loc_to_site:
                out.add(loc_to_site[key])
        return out

    # --------------------------------------------------------------- circuits
    def doped(self, sites: list[Site] | tuple[Site, ...]) -> QuantumCircuit:
        """Checked circuit with T gates inserted at ``sites``."""
        want: dict[int, list[int]] = {}
        for s in sites:
            i, q = self.site_location(s)
            want.setdefault(i, []).append(q)
        out = self.circuit.copy_empty_like()
        for i, inst in enumerate(self.circuit.data):
            out.append(inst)
            for q in want.get(i, []):
                out.t(q)
        return out

    def bare(self, sites=()) -> QuantumCircuit:
        """The same computation with every check removed (and T gates at ``sites``)."""
        return strip_checks(self.doped(sites), self.n)

    # ------------------------------------------------------------- bookkeeping
    def check_gate_columns(self) -> list[list[int]]:
        """For each check, the brickwork layer during which each of its gates acts.

        A check gate is assigned to the layer of the most recent payload CZ on
        its target wire. Used by the web game to draw each check's footprint.
        """
        layer_of = {}
        k = 0
        for layer_idx, layer in enumerate(cz_layers(self.n, self.spec.depth)):
            for _ in layer:
                layer_of[self._cz_pos[k]] = layer_idx
                k += 1
        cols: list[list[int]] = [[] for _ in self.ancillas]
        anc_to_check = {a: i for i, a in enumerate(self.ancillas)}
        last_layer = {q: -1 for q in range(self.n)}
        for i, inst in enumerate(self.circuit.data):
            idx = [self.circuit.find_bit(q).index for q in inst.qubits]
            if i in layer_of:
                for q in idx:
                    last_layer[q] = layer_of[i]
                continue
            if inst.operation.num_qubits == 2:
                anc = [a for a in idx if a in anc_to_check]
                tgt = [q for q in idx if q < self.n]
                if anc and tgt:
                    cols[anc_to_check[anc[0]]].append(last_layer[tgt[0]])
        return cols

    def cost(self) -> dict:
        bare = strip_checks(self.circuit, self.n)
        ops = self.circuit.count_ops()
        n2_total = sum(v for k, v in ops.items() if k in ("cz", "cx", "cy", "ecr"))
        n2_bare = sum(v for k, v in bare.count_ops().items() if k in ("cz", "cx", "cy", "ecr"))
        return {
            "ancillas": len(self.ancillas),
            "added_2q": int(n2_total - n2_bare),
            "depth_2q_bare": int(two_qubit_depth(bare)),
            "depth_2q": int(two_qubit_depth(self.circuit.remove_final_measurements(inplace=False))),
        }

    # kept for uncovered_paulis lookups
    checked_object: object = field(default=None, repr=False)


@lru_cache(maxsize=4096)
def checked_payload(
    spec: PayloadSpec,
    targets: tuple[int, ...],
    profile: NoiseProfile,
    seed: int = 1,
) -> CheckedPayload:
    """Dress ``spec`` with one qiskit-paulice check per qubit in ``targets``.

    Uses ``cost="gamma"`` and ``method="windowed"``, the deterministic setting
    recommended by the qiskit-paulice documentation, so every number in this
    project is exactly reproducible from its seed.
    """
    payload = spec.build()
    measured = payload.copy()
    measured.measure_all()
    targets = tuple(sorted(targets))
    if not targets:
        return CheckedPayload(spec, (), measured, (), (), None, checked_object=None)
    variants = add_pauli_checks(
        measured,
        list(targets),
        profile.paulice(),
        cost="gamma",
        method="windowed",
        seed=seed,
    )
    best = variants[-1]
    obj = CheckedPayload(
        spec=spec,
        targets=tuple(best.target_qubits),
        circuit=best.circuit,
        supports=tuple(best.check_support),
        ancillas=tuple(best.check_qubits),
        gamma=float(best.cost) if best.cost is not None else None,
        checked_object=best,
    )
    return obj


def checked_prefixes(
    spec: PayloadSpec,
    targets: tuple[int, ...],
    profile: NoiseProfile,
    seed: int = 1,
) -> list[CheckedPayload]:
    """All circuits returned by one ``add_pauli_checks`` call (0, 1, ..., k checks).

    This is the "function returns one circuit per number of checks" view
    described in the challenge: checks are committed one at a time in the
    order of ``targets`` and never revised.
    """
    measured = spec.build()
    measured.measure_all()
    variants = add_pauli_checks(
        measured, list(targets), profile.paulice(), cost="gamma", method="windowed", seed=seed
    )
    out = []
    for v in variants:
        out.append(
            CheckedPayload(
                spec=spec,
                targets=tuple(v.target_qubits),
                circuit=v.circuit,
                supports=tuple(v.check_support),
                ancillas=tuple(v.check_qubits),
                gamma=float(v.cost) if v.cost is not None else None,
                checked_object=v if v.check_support else None,
            )
        )
    return out
