from pathlib import Path
from mcp.server.mcpserver import MCPServer

from .resource_uri_algo import ALGO_RESOURCE_URI

_ALGO_HTML_PATH = (
    Path(__file__).resolve().parents[3] / "widget-src" / "generated" / "algo-widget.html"
)


def register_algo_resource(server: MCPServer) -> None:
    @server.resource(
        ALGO_RESOURCE_URI,
        name="algorithm-visualizer-widget",
        description="Interactive 3D Algorithm Step-by-Step Visualizer in Three.js.",
        mime_type="text/html;profile=mcp-app",
    )
    def algo_widget() -> str:
        return _ALGO_HTML_PATH.read_text(encoding="utf-8")
