from .types import Mission
from .off_by_one import off_by_one_sum
from .projectile_motion import projectile_range

_MISSIONS: dict[str, Mission] = {
    off_by_one_sum.id: off_by_one_sum,
    projectile_range.id: projectile_range,
}


def get_mission(mission_id: str) -> Mission:
    mission = _MISSIONS.get(mission_id)
    if mission is None:
        raise ValueError(f"Unknown mission id: {mission_id}")
    return mission


def list_missions() -> list[Mission]:
    return list(_MISSIONS.values())
