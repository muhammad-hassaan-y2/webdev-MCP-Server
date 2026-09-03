import math
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..widget.resource_uri_3d import VISUALIZER_RESOURCE_URI

SAFE_MATH_GLOBALS = {
    "__builtins__": {},
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "pi": math.pi,
    "e": math.e,
    "abs": abs,
    "pow": pow,
}


def register_visualize_math_surface(server: MCPServer) -> None:
    @server.tool(
        name="visualize_math_surface",
        description=(
            "Generates an interactive 3D mathematical surface plot for any function "
            "z = f(x, y). Evaluates the expression across a 2D grid and renders an "
            "interactive Three.js 3D surface mesh inline in chat with orbit controls, "
            "lighting, and grid helpers. Perfect for visualizing calculus, multi-variable "
            "functions, loss surfaces, and wave harmonics."
        ),
        meta={"ui": {"resourceUri": VISUALIZER_RESOURCE_URI}},
    )
    def visualize_math_surface(
        expression: str,
        xRange: list[float] | None = None,
        yRange: list[float] | None = None,
        resolution: int = 24,
        wireframe: bool = False,
        color: str = "#00d2ff",
    ) -> CallToolResult:
        """
        Args:
            expression: Python math expression in terms of x and y, e.g.
                        'sin(sqrt(x**2 + y**2))' or 'x**2 - y**2' or 'cos(x)*sin(y)'.
            xRange: [min_x, max_x], defaults to [-5.0, 5.0].
            yRange: [min_y, max_y], defaults to [-5.0, 5.0].
            resolution: Grid resolution (steps per axis, 10 to 40), default 24.
            wireframe: Whether to render the surface in wireframe mode.
            color: Hex color string for the surface, default '#00d2ff'.
        """
        x_min, x_max = (xRange[0], xRange[1]) if xRange and len(xRange) == 2 else (-5.0, 5.0)
        y_min, y_max = (yRange[0], yRange[1]) if yRange and len(yRange) == 2 else (-5.0, 5.0)
        steps = max(10, min(40, resolution))

        try:
            code_obj = compile(expression, "<string>", "eval")
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Invalid mathematical expression '{expression}': {e}")],
                is_error=True,
            )

        heights = []
        z_min = float("inf")
        z_max = float("-inf")

        width = float(x_max - x_min)
        depth = float(y_max - y_min)

        for j in range(steps + 1):
            y_val = y_min + (depth * j) / steps
            for i in range(steps + 1):
                x_val = x_min + (width * i) / steps
                env = dict(SAFE_MATH_GLOBALS)
                env["x"] = x_val
                env["y"] = y_val
                try:
                    val = float(eval(code_obj, env))
                    if math.isnan(val) or math.isinf(val):
                        val = 0.0
                except Exception:
                    val = 0.0

                val = max(-50.0, min(50.0, val))
                heights.append(round(val, 3))
                if val < z_min:
                    z_min = val
                if val > z_max:
                    z_max = val

        surface_obj = {
            "type": "surface",
            "position": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "color": color,
            "opacity": 0.9,
            "wireframe": wireframe,
            "surfaceGrid": {
                "width": width * 2,
                "depth": depth * 2,
                "segmentsX": steps,
                "segmentsY": steps,
                "heights": heights,
            },
            "animation": {"type": "rotate", "speed": 0.15, "axis": "y"},
            "label": f"z = {expression}",
        }

        scene_spec = {
            "title": f"3D Surface: z = {expression}",
            "description": f"Domain x in [{x_min}, {x_max}], y in [{y_min}, {y_max}] | z range: [{round(z_min, 2)}, {round(z_max, 2)}]",
            "objects": [surface_obj],
            "camera": {
                "position": [width * 1.6, max(depth, z_max - z_min) * 1.5 + 4, depth * 1.6],
                "lookAt": [0, (z_min + z_max) / 4, 0],
            },
            "lights": [
                {"type": "ambient", "color": "#ffffff", "intensity": 0.6, "position": [0, 0, 0]},
                {"type": "directional", "color": "#ffffff", "intensity": 0.8, "position": [15, 25, 15]},
                {"type": "point", "color": "#ffaa00", "intensity": 0.5, "position": [0, z_max + 5, 0]},
            ],
            "gridHelper": True,
            "axesHelper": True,
            "backgroundColor": "#0d1117",
        }

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=(
                        f"Generated 3D mathematical surface for z = {expression}.\n"
                        f"Domain: x in [{x_min}, {x_max}], y in [{y_min}, {y_max}]. "
                        f"Elevation span: {round(z_min, 2)} to {round(z_max, 2)}."
                    ),
                )
            ],
            structured_content={"scene": scene_spec},
            is_error=False,
        )
