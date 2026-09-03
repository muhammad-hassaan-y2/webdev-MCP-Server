from typing import Any
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..widget.resource_uri_physics import PHYSICS_RESOURCE_URI

GRAVITY_PRESETS = {
    "earth": -9.82,
    "moon": -1.62,
    "mars": -3.71,
    "zero_g": 0.0,
    "jupiter": -24.79,
}


def _build_domino_chain(count: int = 14) -> list[dict[str, Any]]:
    objects = []
    spacing = 1.6
    start_x = -((count - 1) * spacing) / 2

    for i in range(count):
        # Slightly tilt the very first domino to initiate the topple reaction
        tilt = 0.2 if i == 0 else 0.0
        objects.append({
            "type": "box",
            "size": [0.4, 3.0, 1.4],
            "position": [start_x + i * spacing, 1.5, 0.0],
            "rotation": [0.0, 0.0, tilt],
            "mass": 2.0,
            "color": "#38bdf8" if i % 2 == 0 else "#f43f5e",
        })
    return objects


def _build_tower_collapse(levels: int = 6) -> list[dict[str, Any]]:
    objects = []
    block_h = 1.0
    for lvl in range(levels):
        y = lvl * block_h + block_h / 2
        is_even = lvl % 2 == 0
        if is_even:
            for offset in [-1.4, 0.0, 1.4]:
                objects.append({
                    "type": "box",
                    "size": [1.2, block_h, 3.8],
                    "position": [offset, y, 0.0],
                    "mass": 1.5,
                    "color": "#fbbf24" if lvl % 2 == 0 else "#34d399",
                })
        else:
            for offset in [-1.4, 0.0, 1.4]:
                objects.append({
                    "type": "box",
                    "size": [3.8, block_h, 1.2],
                    "position": [0.0, y, offset],
                    "mass": 1.5,
                    "color": "#a855f7" if lvl % 2 == 1 else "#38bdf8",
                })
    return objects


def _build_zero_gravity() -> list[dict[str, Any]]:
    objects = []
    colors = ["#38bdf8", "#f43f5e", "#10b981", "#fbbf24", "#a855f7", "#ec4899"]
    for i in range(16):
        import random
        rx = (random.random() - 0.5) * 12
        ry = 3 + random.random() * 8
        rz = (random.random() - 0.5) * 12
        objects.append({
            "type": "sphere" if i % 2 == 0 else "box",
            "size": [1.2, 1.2, 1.2],
            "radius": 0.8,
            "position": [round(rx, 2), round(ry, 2), round(rz, 2)],
            "velocity": [round((random.random() - 0.5) * 4, 2), round((random.random() - 0.5) * 4, 2), round((random.random() - 0.5) * 4, 2)],
            "mass": 1.0,
            "color": colors[i % len(colors)],
        })
    return objects


def register_physics_rigid_body_playground(server: MCPServer) -> None:
    @server.tool(
        name="physics_rigid_body_playground",
        description=(
            "Renders an interactive 3D rigid-body physics simulation in chat powered by "
            "Cannon-es and Three.js. Supports true physical gravity, mass, inertia, friction, "
            "and collision dynamics. Includes interactive scenes: 'domino_chain' (toppling dominoes), "
            "'tower_collapse' (destructible block towers), and 'zero_gravity_collision' (floating orbital objects). "
            "Users can change gravity in real time (Earth, Moon, Mars, Zero-G, Jupiter), click to blast cannonballs, "
            "and spawn rigid objects."
        ),
        meta={"ui": {"resourceUri": PHYSICS_RESOURCE_URI}},
    )
    def physics_rigid_body_playground(
        sceneType: str = "domino_chain",
        gravityPreset: str = "earth",
        restitution: float = 0.5,
        friction: float = 0.4,
    ) -> CallToolResult:
        """
        Args:
            sceneType: Scene setup: 'domino_chain', 'tower_collapse', or 'zero_gravity_collision'.
            gravityPreset: Gravity setting: 'earth' (-9.82 m/s²), 'moon' (-1.62 m/s²), 'mars' (-3.71 m/s²), 'zero_g' (0.0 m/s²), 'jupiter' (-24.79 m/s²).
            restitution: Bounciness coefficient from 0.0 (inelastic) to 0.95 (super bouncy).
            friction: Surface friction from 0.0 (ice) to 1.0 (sticky rubber).
        """
        stype = sceneType.lower().replace("-", "_").strip()
        g_key = gravityPreset.lower().replace("-", "_").strip()
        gravity_val = GRAVITY_PRESETS.get(g_key, -9.82)
        rest = max(0.0, min(0.95, restitution))
        fric = max(0.0, min(1.0, friction))

        if stype == "tower_collapse":
            objects = _build_tower_collapse(levels=6)
            title = "Jenga Tower Demolition"
            desc = "Stack of balanced rigid blocks. Click anywhere or shoot cannonballs to topple the tower!"
        elif stype == "zero_gravity_collision":
            objects = _build_zero_gravity()
            gravity_val = 0.0
            title = "Zero-Gravity Orbital Collisions"
            desc = "Floating rigid bodies in deep space with zero gravity and continuous momentum exchange."
        else:
            objects = _build_domino_chain(count=14)
            stype = "domino_chain"
            title = "Toppling Domino Chain Reaction"
            desc = "Aligned domino blocks with kinetic momentum transfer. First domino initiates the cascade."

        payload = {
            "title": title,
            "description": desc,
            "sceneType": stype,
            "gravity": gravity_val,
            "gravityPreset": g_key,
            "restitution": rest,
            "friction": fric,
            "objects": objects,
        }

        summary = (
            f"Initialized 3D Rigid-Body Physics Playground: '{title}'\n"
            f"• Physics Engine: Cannon-es (60 Hz continuous collision)\n"
            f"• Gravity: {gravity_val} m/s² ({g_key.title()})\n"
            f"• Restitution (Bounciness): {rest}\n"
            f"• Friction: {fric}\n"
            f"• Active Rigid Bodies: {len(objects)}\n"
            f"Click inside the 3D canvas to fire heavy cannonballs!"
        )

        return CallToolResult(
            content=[TextContent(type="text", text=summary)],
            structured_content={"physicsWorld": payload},
            is_error=False,
        )
