from pathlib import Path
from mcp.server.mcpserver import MCPServer

from .resource_uri import WIDGET_RESOURCE_URI

# widget-src/generated/mission-widget.html is produced by `npm run build:widget`
# (esbuild bundles the TS/JS widget source, including Three.js for the
# simulation UI, and inlines it into this HTML file). The server just reads
# and serves that pre-built file - Python never needs to touch JS/WebGL code.
_WIDGET_HTML_PATH = (
    Path(__file__).resolve().parents[3] / "widget-src" / "generated" / "mission-widget.html"
)


def register_widget_resource(server: MCPServer) -> None:
    @server.resource(
        WIDGET_RESOURCE_URI,
        name="debug-mission-widget",
        description="Interactive editor/simulation + grading widget for a mission.",
        # text/html;profile=mcp-app is the MCP Apps convention for UI resources.
        mime_type="text/html;profile=mcp-app",
    )
    def widget() -> str:
        return _WIDGET_HTML_PATH.read_text(encoding="utf-8")
