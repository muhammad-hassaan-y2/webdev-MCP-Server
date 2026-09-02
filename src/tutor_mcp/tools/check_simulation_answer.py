from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..missions.registry import get_mission
from ..sandbox.physics import check_simulation_answer as _check


def register_check_simulation_answer(server: MCPServer) -> None:
    @server.tool(
        name="check_simulation_answer",
        description=(
            "Checks a student's numeric prediction for a SIMULATION mission (e.g. "
            "projectile range) against a real computation using the exact "
            "parameters the student chose. This is the only source of truth for "
            "correctness on simulation missions - never decide pass/fail from the "
            "model's own math."
        ),
    )
    def check_simulation_answer(
        missionId: str, params: dict[str, float], studentAnswer: float
    ) -> CallToolResult:
        """
        Args:
            missionId: The mission id.
            params: The parameter values the student set, e.g. {"angle": 30, "velocity": 20}.
            studentAnswer: The student's numeric prediction.
        """
        mission = get_mission(missionId)
        if mission.type != "simulation":
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Mission {missionId} is a {mission.type} mission, not a "
                            "simulation. Use run_tests instead."
                        ),
                    )
                ],
                is_error=True,
            )

        result = _check(missionId, params, studentAnswer)
        text = (
            f"Correct - actual value is {result.actual:.2f}."
            if result.passed
            else f"Not quite - actual value is {result.actual:.2f}, you said {studentAnswer}."
        )
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content=result.model_dump(by_alias=True),
            is_error=False,
        )
