from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..missions.registry import get_mission
from ..sandbox.run_python import run_python_tests
from ..sandbox.physics import check_simulation_answer
from ..store.progress_store import record_attempt


def register_record_progress(server: MCPServer) -> None:
    @server.tool(
        name="record_progress",
        description=(
            "Records a student's attempt at a mission (code or simulation). This "
            "tool NEVER trusts a claim that the student passed - whether that "
            "claim comes from the widget, the conversation, or a model. It always "
            "re-runs the correct deterministic check itself (re-executing code, "
            "or recomputing the real physics/math) and only marks the mission "
            "complete if that fresh check passes. This is the single place "
            "mastery state is written."
        ),
    )
    def record_progress(
        missionId: str,
        studentId: str,
        code: str | None = None,
        params: dict[str, float] | None = None,
        studentAnswer: float | None = None,
    ) -> CallToolResult:
        """
        Args:
            missionId: The mission id.
            studentId: Stable student identifier.
            code: Required for code missions.
            params: Required for simulation missions: the parameters used.
            studentAnswer: Required for simulation missions.
        """
        mission = get_mission(missionId)

        if mission.type == "code":
            if code is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="code is required for a code mission.")],
                    is_error=True,
                )
            # Re-run for real. The client may have already shown a "pass"
            # locally, but that result never reaches this store - only this
            # fresh run does.
            run = run_python_tests(code, mission.function_name, mission.tests)
            all_passed = run.all_passed
            detail = run.model_dump(by_alias=True)
        else:
            if params is None or studentAnswer is None:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="params and studentAnswer are required for a simulation mission.",
                        )
                    ],
                    is_error=True,
                )
            # Same principle: recompute the real physics server-side rather
            # than trusting whatever the widget already displayed.
            result = check_simulation_answer(missionId, params, studentAnswer)
            all_passed = result.passed
            detail = result.model_dump(by_alias=True)

        completed, attempts = record_attempt(studentId, missionId, all_passed)

        text = (
            f"Verified server-side: correct. Mission recorded as complete (attempt {attempts})."
            if all_passed
            else f"Server-side re-check did not confirm a pass (attempt {attempts}). Not recorded as complete."
        )
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content={
                "allPassed": all_passed,
                "completed": completed,
                "attempts": attempts,
                "detail": detail,
            },
            is_error=False,
        )
