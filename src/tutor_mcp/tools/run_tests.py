from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..missions.registry import get_mission
from ..sandbox.run_python import run_python_tests


def register_run_tests(server: MCPServer) -> None:
    @server.tool(
        name="run_tests",
        description=(
            "Runs a student's Python function against a CODE mission's fixed test "
            "cases and returns real pass/fail results. This is the ONLY source of "
            "truth for correctness - callers must not report a mission as passed "
            "unless this tool (or record_progress, which re-runs this same check) "
            "says allPassed is true. Only use this for code missions - use "
            "check_simulation_answer for simulations."
        ),
    )
    def run_tests(missionId: str, code: str) -> CallToolResult:
        """
        Args:
            missionId: The mission id.
            code: The student's current Python source code.
        """
        mission = get_mission(missionId)
        if mission.type != "code":
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Mission {missionId} is a {mission.type} mission, not a "
                            "code mission. Use check_simulation_answer instead."
                        ),
                    )
                ],
                is_error=True,
            )

        result = run_python_tests(code, mission.function_name, mission.tests)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="All tests passed." if result.all_passed else (result.load_error or "Some tests failed."),
                )
            ],
            structured_content=result.model_dump(by_alias=True),
            is_error=False,
        )
