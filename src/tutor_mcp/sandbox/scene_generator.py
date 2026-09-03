"""
Generates structured 3D scene specifications from natural language queries
using the Gemini API. The output is a JSON-serializable dict describing
objects, camera, lights, and animations that the visualizer widget renders
with Three.js.

If GEMINI_API_KEY is not set, returns a simple fallback scene.
"""

import json
import os
from typing import Any

import httpx

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SCENE_SYSTEM_PROMPT = """\
You are a 3D scene generator. Given a user's description, output ONLY valid JSON
(no markdown fences, no explanation) describing a Three.js scene.

The JSON must follow this exact schema:

{
  "title": "string - short title for the visualization",
  "description": "string - one sentence explaining what is shown",
  "objects": [
    {
      "type": "box" | "sphere" | "cylinder" | "torus" | "cone" | "ring" | "plane",
      "position": [x, y, z],
      "rotation": [x, y, z],
      "scale": [x, y, z],
      "color": "#hexcolor",
      "opacity": 1.0,
      "label": "optional string label",
      "animation": {
        "type": "rotate" | "orbit" | "bounce" | "pulse" | "none",
        "speed": 1.0,
        "axis": "x" | "y" | "z",
        "orbitRadius": 5.0,
        "orbitCenter": [0, 0, 0]
      }
    }
  ],
  "camera": {
    "position": [x, y, z],
    "lookAt": [x, y, z]
  },
  "lights": [
    {
      "type": "ambient" | "directional" | "point",
      "color": "#hexcolor",
      "intensity": 1.0,
      "position": [x, y, z]
    }
  ],
  "gridHelper": true | false,
  "axesHelper": true | false,
  "backgroundColor": "#hexcolor"
}

Rules:
- Output ONLY the JSON object, nothing else.
- Keep positions within [-50, 50] range for each axis.
- Use realistic, visually appealing hex colors.
- Include at least one ambient light and one directional light.
- For solar system / space scenes, use dark background (#0a0a1a), disable grid.
- For math/geometry scenes, enable grid and axes helpers.
- For orbit animations, set orbitRadius and orbitCenter appropriately.
- Maximum 20 objects to keep rendering smooth.
- Make scenes visually interesting with varied colors and animations.
"""

DEFAULT_SCENE: dict[str, Any] = {
    "title": "Default Scene",
    "description": "A rotating cube — Gemini API key not set or generation failed.",
    "objects": [
        {
            "type": "box",
            "position": [0, 1, 0],
            "rotation": [0, 0, 0],
            "scale": [2, 2, 2],
            "color": "#4a90d9",
            "opacity": 1.0,
            "label": "Cube",
            "animation": {"type": "rotate", "speed": 1.0, "axis": "y"},
        }
    ],
    "camera": {"position": [5, 5, 5], "lookAt": [0, 1, 0]},
    "lights": [
        {"type": "ambient", "color": "#ffffff", "intensity": 0.6, "position": [0, 0, 0]},
        {"type": "directional", "color": "#ffffff", "intensity": 0.8, "position": [10, 15, 10]},
    ],
    "gridHelper": True,
    "axesHelper": True,
    "backgroundColor": "#1a1a2e",
}


def validate_scene_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate and sanitize a scene spec, capping values to safe ranges."""
    # Ensure required fields
    if "title" not in spec:
        spec["title"] = "3D Visualization"
    if "description" not in spec:
        spec["description"] = ""
    if "objects" not in spec or not isinstance(spec["objects"], list):
        spec["objects"] = DEFAULT_SCENE["objects"]
    if "camera" not in spec:
        spec["camera"] = DEFAULT_SCENE["camera"]
    if "lights" not in spec or not isinstance(spec["lights"], list):
        spec["lights"] = DEFAULT_SCENE["lights"]

    # Cap objects at 20
    spec["objects"] = spec["objects"][:20]

    # Clamp positions to safe range
    for obj in spec["objects"]:
        if "position" in obj:
            obj["position"] = [max(-50, min(50, v)) for v in obj["position"]]
        if "scale" in obj:
            obj["scale"] = [max(0.01, min(20, v)) for v in obj["scale"]]
        # Ensure required fields
        if "type" not in obj:
            obj["type"] = "box"
        if "color" not in obj:
            obj["color"] = "#4a90d9"
        if "opacity" not in obj:
            obj["opacity"] = 1.0
        if "animation" not in obj:
            obj["animation"] = {"type": "none"}

    # Ensure booleans
    spec.setdefault("gridHelper", False)
    spec.setdefault("axesHelper", False)
    spec.setdefault("backgroundColor", "#1a1a2e")

    return spec


async def generate_scene_spec(
    query: str, scene_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Generate a 3D scene specification from a natural language query.

    Uses Gemini to interpret the query and produce structured JSON that the
    visualizer widget can render. Falls back to DEFAULT_SCENE if Gemini is
    unavailable.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        fallback = dict(DEFAULT_SCENE)
        fallback["title"] = query[:60]
        fallback["description"] = (
            "Showing default scene — set GEMINI_API_KEY for AI-generated visualizations."
        )
        return fallback

    user_text = f"Create a 3D scene for: {query}"
    if scene_config:
        user_text += f"\n\nAdditional configuration: {json.dumps(scene_config)}"

    body = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "systemInstruction": {"parts": [{"text": SCENE_SYSTEM_PROMPT}]},
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.7,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                GEMINI_URL_TMPL.format(model=GEMINI_MODEL),
                params={"key": api_key},
                json=body,
            )
        if resp.status_code != 200:
            return _fallback_with_query(query)

        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()

        # Strip markdown code fences if Gemini wraps them anyway
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        spec = json.loads(text)
        return validate_scene_spec(spec)

    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError):
        return _fallback_with_query(query)


def _fallback_with_query(query: str) -> dict[str, Any]:
    fallback = dict(DEFAULT_SCENE)
    fallback["title"] = query[:60]
    fallback["description"] = "Gemini generation failed — showing default scene."
    return fallback
