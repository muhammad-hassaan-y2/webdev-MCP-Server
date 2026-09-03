from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..sandbox.scene_generator import generate_scene_spec
from ..widget.resource_uri_3d import VISUALIZER_RESOURCE_URI


def register_generate_3d_scene(server: MCPServer) -> None:
    @server.tool(
        name="generate_3d_scene",
        description=(
            "Generates an interactive 3D visualization from a natural language "
            "description. Use this when a student asks to see or visualize "
            "something in 3D — a solar system, molecular structure, geometric "
            "shape, wave function, coordinate system, or any spatial concept. "
            "Renders an interactive Three.js scene inline in the chat that the "
            "student can rotate, zoom, and explore."
        ),
        meta={"ui": {"resourceUri": VISUALIZER_RESOURCE_URI}},
    )
    async def generate_3d_scene(
        query: str,
        sceneConfig: dict | None = None,
    ) -> CallToolResult:
        """
        Args:
            query: Natural language description of what to visualize, e.g.
                   'a solar system with orbiting planets' or 'a rotating DNA helix'.
            sceneConfig: Optional overrides for camera, lighting, background, etc.
        """
        scene_spec = await generate_scene_spec(query, sceneConfig)

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=(
                        f'Generated 3D scene: "{scene_spec.get("title", query)}". '
                        f'{scene_spec.get("description", "")}'
                    ),
                )
            ],
            structured_content={"scene": scene_spec},
            is_error=False,
        )
