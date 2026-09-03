from pathlib import Path
from mcp.server.mcpserver import MCPServer

from .resource_uri_sandbox import SANDBOX_RESOURCE_URI

# sandbox-widget.html is produced by `npm run build:widget` alongside the
# mission and visualizer widgets. It contains the interactive HTML/CSS/JS sandbox.
_SANDBOX_HTML_PATH = (
    Path(__file__).resolve().parents[3] / "widget-src" / "generated" / "sandbox-widget.html"
)


def register_sandbox_resource(server: MCPServer) -> None:
    @server.resource(
        SANDBOX_RESOURCE_URI,
        name="web-sandbox-widget",
        description="Interactive live HTML/CSS/JS preview and sandbox widget.",
        mime_type="text/html;profile=mcp-app",
    )
    def sandbox_widget() -> str:
        return _SANDBOX_HTML_PATH.read_text(encoding="utf-8")
