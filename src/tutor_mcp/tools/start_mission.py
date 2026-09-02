from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..missions.registry import get_mission
from ..widget.resource_uri import WIDGET_RESOURCE_URI


def register_start_mission(server: MCPServer) -> None:
    @server.tool(
        name="start_mission",
        description=(
            "Starts an interactive mission for a student on a specific concept - "
            "either a code-debugging exercise or a hands-on simulation (e.g. "
            "physics). Call this when a student is stuck on a concept and would "
            "benefit from a gradable, interactive exercise rather than a text "
            "explanation. Renders an interactive widget."
        ),
        # This is what turns a plain tool call into a rendered widget: the host
        # looks up this resource and shows it inline instead of (or alongside)
        # the text response.
        meta={"ui": {"resourceUri": WIDGET_RESOURCE_URI}},
    )
    def start_mission(missionId: str, studentId: str) -> CallToolResult:
        """
        Args:
            missionId: Mission id, e.g. 'off-by-one-sum' or 'projectile-range'
            studentId: Stable identifier for the student, used to track progress
        """
        mission = get_mission(missionId)
        payload = {
            "mission": mission.model_dump(by_alias=True),
            "studentId": studentId,
        }
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f'Started "{mission.title}" ({mission.concept}) for student {studentId}.',
                )
            ],
            structured_content=payload,
            is_error=False,
        )
