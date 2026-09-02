import math
from typing import Callable
from ..missions.types import CamelModel


class SimulationCheckResult(CamelModel):
    actual: float
    student_answer: float
    passed: bool
    tolerance: float


def _projectile_range(params: dict[str, float]) -> float:
    g = 9.8
    angle = params["angle"]
    velocity = params["velocity"]
    radians = math.radians(angle)
    return (velocity**2 * math.sin(2 * radians)) / g


# One real formula per simulation mission id. This is the ground truth - the
# widget may draw its own approximate trajectory for visual feedback, but the
# number that decides pass/fail always comes from here, computed server-side
# from the parameters the student actually chose, never from anything the
# model or the client claims the answer is.
_FORMULAS: dict[str, Callable[[dict[str, float]], float]] = {
    "projectile-range": _projectile_range,
}


def check_simulation_answer(
    mission_id: str, params: dict[str, float], student_answer: float
) -> SimulationCheckResult:
    formula = _FORMULAS.get(mission_id)
    if formula is None:
        raise ValueError(f"No physics formula registered for mission {mission_id}")

    actual = formula(params)
    # Generous tolerance: 5% relative error or 0.5 units, whichever is larger,
    # to allow for reasonable rounding in the student's mental math.
    tolerance = max(0.5, 0.05 * abs(actual))
    passed = abs(actual - student_answer) <= tolerance
    return SimulationCheckResult(
        actual=actual, student_answer=student_answer, passed=passed, tolerance=tolerance
    )
