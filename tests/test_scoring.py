from sentinels.scoring import fidelity_rate, pareto_front, stars


def test_rate():
    assert fidelity_rate(0.9, 0.81, 0.5) == 0.9 * 0.9
    assert fidelity_rate(0.9, 0.0) == 0.0


def test_stars():
    assert stars(0.70, 0.70, 0.80) == 0
    assert stars(0.75, 0.70, 0.80) == 1
    assert stars(0.79, 0.70, 0.80) == 2
    assert stars(0.80, 0.70, 0.80) == 3


def test_pareto():
    pts = [(1.0, 0.6), (0.8, 0.8), (0.7, 0.7), (0.5, 0.9)]
    assert pareto_front(pts) == [3, 1, 0]
