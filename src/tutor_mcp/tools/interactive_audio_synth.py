from typing import Any
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..widget.resource_uri_audio import AUDIO_RESOURCE_URI

PRESETS: dict[str, dict[str, Any]] = {
    "cyberpunk_lead": {
        "title": "Cyberpunk Synth Lead",
        "waveform": "sawtooth",
        "baseFrequency": 220.0,
        "filterCutoff": 1800.0,
        "resonance": 8.0,
        "harmonics": [1.0, 0.5, 0.33, 0.25, 0.2],
        "description": "Aggressive saw lead with resonant low-pass filter, common in cyberpunk and synthwave.",
        "equation": "f(t) = \\sum_{k=1}^N \\frac{(-1)^{k+1}}{k} \\sin(2\\pi k f t)",
    },
    "space_ambient": {
        "title": "Deep Space Ambient Pad",
        "waveform": "sine",
        "baseFrequency": 110.0,
        "filterCutoff": 800.0,
        "resonance": 2.0,
        "harmonics": [1.0, 0.2, 0.05],
        "description": "Warm fundamental sine tone with gentle harmonics simulating deep interstellar atmosphere.",
        "equation": "f(t) = A_1 \\sin(2\\pi f t) + A_2 \\sin(4\\pi f t)",
    },
    "harmonic_series": {
        "title": "Harmonic Series Explorer",
        "waveform": "triangle",
        "baseFrequency": 440.0,
        "filterCutoff": 2400.0,
        "resonance": 1.0,
        "harmonics": [1.0, 0.0, 0.11, 0.0, 0.04],
        "description": "Odd harmonic series demonstration showing Fourier synthesis of triangle waves.",
        "equation": "f(t) = \\sum_{n=1,3,5...} \\frac{(-1)^{(n-1)/2}}{n^2} \\sin(2\\pi n f t)",
    },
    "sub_bass": {
        "title": "808 Heavy Sub Bass",
        "waveform": "sine",
        "baseFrequency": 55.0,
        "filterCutoff": 300.0,
        "resonance": 4.0,
        "harmonics": [1.0, 0.15],
        "description": "Pure low-frequency pressure wave (A1 note at 55Hz) with subtle upper warmth.",
        "equation": "f(t) = A \\sin(2\\pi (55) t)",
    },
}


def register_interactive_audio_synth(server: MCPServer) -> None:
    @server.tool(
        name="interactive_audio_synth",
        description=(
            "Renders an interactive Web Audio frequency synthesizer directly inside chat. "
            "Features real-time audio generation, playable piano keys, waveform toggles "
            "(sine, square, sawtooth, triangle), frequency and filter knobs, and a live "
            "oscilloscope visualizing sound wave harmonics in real time. Perfect for learning "
            "acoustics, Fourier harmonics, pitch frequencies, and sound synthesis."
        ),
        meta={"ui": {"resourceUri": AUDIO_RESOURCE_URI}},
    )
    def interactive_audio_synth(
        preset: str = "cyberpunk_lead",
        waveform: str | None = None,
        baseFrequency: float | None = None,
        filterCutoff: float | None = None,
    ) -> CallToolResult:
        """
        Args:
            preset: Preset configuration: 'cyberpunk_lead', 'space_ambient', 'harmonic_series', 'sub_bass'.
            waveform: Override waveform: 'sine', 'sawtooth', 'square', 'triangle'.
            baseFrequency: Base pitch in Hz (e.g. 440.0 for Concert A, 261.63 for Middle C).
            filterCutoff: Lowpass filter cutoff frequency in Hz (100 to 5000).
        """
        key = preset.lower().replace("-", "_").strip()
        config = dict(PRESETS.get(key, PRESETS["cyberpunk_lead"]))

        if waveform and waveform in ["sine", "sawtooth", "square", "triangle"]:
            config["waveform"] = waveform
        if baseFrequency and 20.0 <= baseFrequency <= 4000.0:
            config["baseFrequency"] = round(baseFrequency, 2)
        if filterCutoff and 50.0 <= filterCutoff <= 10000.0:
            config["filterCutoff"] = round(filterCutoff, 2)

        summary = (
            f"Synthesizer configured with preset '{config['title']}':\n"
            f"• Waveform: {config['waveform']}\n"
            f"• Fundamental Frequency: {config['baseFrequency']} Hz\n"
            f"• Filter Cutoff: {config['filterCutoff']} Hz\n"
            f"• Wave Equation: {config['equation']}\n"
            f"Interactive audio keys and live oscilloscope rendered in widget."
        )

        return CallToolResult(
            content=[TextContent(type="text", text=summary)],
            structured_content={"synthConfig": config},
            is_error=False,
        )
