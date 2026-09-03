from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..widget.resource_uri_sandbox import SANDBOX_RESOURCE_URI


def register_preview_html_css(server: MCPServer) -> None:
    @server.tool(
        name="preview_html_css",
        description=(
            "Renders a live, interactive web development sandbox directly inside "
            "the chat. Takes HTML, CSS, and optional JavaScript and displays an "
            "interactive preview with live code tabs. Use this whenever the user "
            "asks to design, build, or preview web components, UI mockups, buttons, "
            "cards, landing pages, CSS animations, or frontend widgets."
        ),
        meta={"ui": {"resourceUri": SANDBOX_RESOURCE_URI}},
    )
    def preview_html_css(
        html: str,
        css: str = "",
        javascript: str = "",
        title: str = "Web Component Preview",
    ) -> CallToolResult:
        """
        Args:
            html: HTML markup for the component or page.
            css: CSS styling rules.
            javascript: Optional JavaScript behavior/interactivity.
            title: Friendly title for the component or widget.
        """
        payload = {
            "title": title or "Web Component Preview",
            "html": html or "<div style='padding: 20px;'>Hello World</div>",
            "css": css or "",
            "javascript": javascript or "",
        }

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=(
                        f"Rendered interactive web preview: '{payload['title']}'. "
                        f"Includes {len(html)} chars HTML, {len(css)} chars CSS, {len(javascript)} chars JS."
                    ),
                )
            ],
            structured_content={"sandbox": payload},
            is_error=False,
        )
