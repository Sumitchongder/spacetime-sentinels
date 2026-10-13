from qiskit.quantum_info import Clifford

from sentinels.payloads import all_sites, brickwork_clifford, cz_layers, site_order


def test_payload_is_clifford_and_deterministic():
    a = brickwork_clifford(6, 8, 7)
    b = brickwork_clifford(6, 8, 7)
    assert Clifford(a) == Clifford(b)
    assert set(a.count_ops()) <= {"h", "cz", "sx", "s"}


def test_layers_and_sites():
    layers = cz_layers(6, 4)
    assert layers[0] == [(0, 1), (2, 3), (4, 5)]
    assert layers[1] == [(1, 2), (3, 4)]
    assert len(all_sites(6, 4)) == 2 * sum(len(x) for x in layers)
    order = site_order(6, 4, 7)
    assert sorted(order) == sorted(all_sites(6, 4))
    assert order == site_order(6, 4, 7)
