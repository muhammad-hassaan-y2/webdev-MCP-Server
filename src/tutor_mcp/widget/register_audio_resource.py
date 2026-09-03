from pathlib import Path
from mcp.server.mcpserver import MCPServer

from .resource_uri_audio import AUDIO_RESOURCE_URI

_AUDIO_HTML_PATH = (
    Path(__file__).resolve().parents[3] / "widget-src" / "generated" / "audio-synth-widget.html"
)


def register_audio_resource(server: MCPServer) -> None:
    @server.resource(
        AUDIO_RESOURCE_URI,
        name="audio-synthesizer-widget",
        description="Interactive Web Audio Synthesizer with real-time waveform oscilloscope.",
        mime_type="text/html;profile=mcp-app",
    )
    def audio_widget() -> str:
        return _AUDIO_HTML_PATH.read_text(encoding="utf-8")
