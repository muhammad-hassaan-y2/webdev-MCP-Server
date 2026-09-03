import os
from mcp.server.mcpserver import MCPServer

from .tools.start_mission import register_start_mission
from .tools.run_tests import register_run_tests
from .tools.check_simulation_answer import register_check_simulation_answer
from .tools.get_hint import register_get_hint
from .tools.record_progress import register_record_progress
from .tools.generate_3d_scene import register_generate_3d_scene
from .widget.register_resource import register_widget_resource
from .widget.register_visualizer_resource import register_visualizer_resource


def build_server() -> MCPServer:
    server = MCPServer(name="interactive-tutor", version="1.0.0")

    register_start_mission(server)
    register_run_tests(server)
    register_check_simulation_answer(server)
    register_get_hint(server)
    register_record_progress(server)
    register_generate_3d_scene(server)
    register_widget_resource(server)
    register_visualizer_resource(server)

    return server


def main() -> None:
    server = build_server()
    port = int(os.environ.get("PORT", "3000"))

    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY not set - get_hint will use static fallback hints instead of AI-generated ones.")

    print(f"Tutor MCP server listening on http://0.0.0.0:{port}/mcp")
    server.run(transport="streamable-http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
