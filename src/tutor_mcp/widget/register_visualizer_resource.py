from pathlib import Path
from mcp.server.mcpserver import MCPServer

from .resource_uri_3d import VISUALIZER_RESOURCE_URI

# visualizer-widget.html is produced by `npm run build:widget` alongside the
# mission widget. It contains the Three.js-based 3D scene renderer.
_VISUALIZER_HTML_PATH = (
    Path(__file__).resolve().parents[3] / "widget-src" / "generated" / "visualizer-widget.html"
)


def register_visualizer_resource(server: MCPServer) -> None:
    @server.resource(
        VISUALIZER_RESOURCE_URI,
        name="3d-visualizer-widget",
        description="Interactive 3D scene visualizer powered by Three.js.",
        mime_type="text/html;profile=mcp-app",
    )
    def visualizer_widget() -> str:
        return _VISUALIZER_HTML_PATH.read_text(encoding="utf-8")
