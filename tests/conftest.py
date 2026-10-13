import pytest

from sentinels import PayloadSpec, get_profile


@pytest.fixture(scope="session")
def profile():
    return get_profile("qff-synthetic")


@pytest.fixture(scope="session")
def spec():
    return PayloadSpec(num_qubits=5, depth=6, seed=3)
