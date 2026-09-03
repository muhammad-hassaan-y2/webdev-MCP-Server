import os
from dotenv import load_dotenv
load_dotenv()
from mcp.server.mcpserver import MCPServer

from .tools.start_mission import register_start_mission
from .tools.run_tests import register_run_tests
from .tools.check_simulation_answer import register_check_simulation_answer
from .tools.get_hint import register_get_hint
from .tools.record_progress import register_record_progress
from .tools.generate_3d_scene import register_generate_3d_scene
from .tools.visualize_math_surface import register_visualize_math_surface
from .tools.preview_html_css import register_preview_html_css
from .tools.run_code_scratchpad import register_run_code_scratchpad
from .tools.get_student_analytics import register_get_student_analytics
from .tools.visualize_algorithm_3d import register_visualize_algorithm_3d
from .tools.interactive_audio_synth import register_interactive_audio_synth
from .tools.physics_rigid_body_playground import register_physics_rigid_body_playground
from .widget.register_resource import register_widget_resource
from .widget.register_visualizer_resource import register_visualizer_resource
from .widget.register_sandbox_resource import register_sandbox_resource
from .widget.register_algo_resource import register_algo_resource
from .widget.register_audio_resource import register_audio_resource
from .widget.register_physics_playground_resource import register_physics_playground_resource


def build_server() -> MCPServer:
    server = MCPServer(name="interactive-tutor", version="1.0.0")

    register_start_mission(server)
    register_run_tests(server)
    register_check_simulation_answer(server)
    register_get_hint(server)
    register_record_progress(server)
    register_generate_3d_scene(server)
    register_visualize_math_surface(server)
    register_preview_html_css(server)
    register_run_code_scratchpad(server)
    register_get_student_analytics(server)
    register_visualize_algorithm_3d(server)
    register_interactive_audio_synth(server)
    register_physics_rigid_body_playground(server)

    register_widget_resource(server)
    register_visualizer_resource(server)
    register_sandbox_resource(server)
    register_algo_resource(server)
    register_audio_resource(server)
    register_physics_playground_resource(server)

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
