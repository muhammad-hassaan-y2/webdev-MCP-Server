from pathlib import Path
from mcp.server.mcpserver import MCPServer

from .resource_uri_physics import PHYSICS_RESOURCE_URI

_PHYSICS_HTML_PATH = (
    Path(__file__).resolve().parents[3] / "widget-src" / "generated" / "physics-playground-widget.html"
)


def register_physics_playground_resource(server: MCPServer) -> None:
    @server.resource(
        PHYSICS_RESOURCE_URI,
        name="physics-playground-widget",
        description="Interactive 3D Rigid-Body Physics Playground powered by Three.js and Cannon-es.",
        mime_type="text/html;profile=mcp-app",
    )
    def physics_widget() -> str:
        return _PHYSICS_HTML_PATH.read_text(encoding="utf-8")
