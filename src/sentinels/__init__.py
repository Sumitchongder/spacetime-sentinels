"""Spacetime Sentinels: a game of low-overhead error detection with spacetime codes.

Every score in the game is computed with Qiskit: checks are placed with
qiskit-paulice, ideal states come from stabilizer or statevector simulation,
and noisy, post-selected states come from Qiskit Aer.
"""

from .checks import CheckedPayload, checked_payload, strip_checks
from .experiment import POLICIES, evaluate_configuration, run_grid, subsets
from .fidelity import Evaluation, exact_evaluation, noiseless_false_alarms, reference_state
from .noise import NoiseProfile, get_profile
from .payloads import PayloadSpec, brickwork_clifford, site_order
from .scoring import fidelity_rate, pareto_front, stars

__version__ = "1.0.0"

__all__ = [
    "CheckedPayload",
    "Evaluation",
    "NoiseProfile",
    "POLICIES",
    "PayloadSpec",
    "brickwork_clifford",
    "checked_payload",
    "evaluate_configuration",
    "exact_evaluation",
    "fidelity_rate",
    "get_profile",
    "noiseless_false_alarms",
    "pareto_front",
    "reference_state",
    "run_grid",
    "site_order",
    "stars",
    "strip_checks",
    "subsets",
    "__version__",
]
