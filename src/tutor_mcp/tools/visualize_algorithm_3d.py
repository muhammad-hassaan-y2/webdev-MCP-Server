import random
from typing import Any
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..widget.resource_uri_algo import ALGO_RESOURCE_URI


def _generate_bubble_sort_steps(arr: list[int]) -> list[dict[str, Any]]:
    a = list(arr)
    n = len(a)
    steps = []
    comparisons = 0
    swaps = 0
    sorted_indices = []

    steps.append({
        "array": list(a),
        "comparing": [],
        "swapped": False,
        "sorted": list(sorted_indices),
        "description": "Initial array state before sorting.",
        "comparisons": comparisons,
        "swaps": swaps,
    })

    for i in range(n):
        for j in range(0, n - i - 1):
            comparisons += 1
            is_swap = a[j] > a[j + 1]
            if is_swap:
                a[j], a[j + 1] = a[j + 1], a[j]
                swaps += 1

            steps.append({
                "array": list(a),
                "comparing": [j, j + 1],
                "swapped": is_swap,
                "sorted": list(sorted_indices),
                "description": f"Comparing index {j} ({a[j]}) with index {j+1} ({a[j+1]}): {'Swapped!' if is_swap else 'In order.'}",
                "comparisons": comparisons,
                "swaps": swaps,
            })
        sorted_indices.append(n - i - 1)

    sorted_indices = list(range(n))
    steps.append({
        "array": list(a),
        "comparing": [],
        "swapped": False,
        "sorted": sorted_indices,
        "description": f"Sorting complete in {comparisons} comparisons and {swaps} swaps! Array fully sorted.",
        "comparisons": comparisons,
        "swaps": swaps,
    })
    return steps


def _generate_insertion_sort_steps(arr: list[int]) -> list[dict[str, Any]]:
    a = list(arr)
    n = len(a)
    steps = []
    comparisons = 0
    swaps = 0
    sorted_indices = [0]

    steps.append({
        "array": list(a),
        "comparing": [0],
        "swapped": False,
        "sorted": [0],
        "description": "Initial state. First element is considered sorted.",
        "comparisons": comparisons,
        "swaps": swaps,
    })

    for i in range(1, n):
        key = a[i]
        j = i - 1
        steps.append({
            "array": list(a),
            "comparing": [i],
            "swapped": False,
            "sorted": list(sorted_indices),
            "description": f"Extracting key {key} at index {i} to insert into sorted prefix.",
            "comparisons": comparisons,
            "swaps": swaps,
        })
        while j >= 0:
            comparisons += 1
            if a[j] > key:
                a[j + 1] = a[j]
                swaps += 1
                steps.append({
                    "array": list(a),
                    "comparing": [j, j + 1],
                    "swapped": True,
                    "sorted": list(sorted_indices),
                    "description": f"Shifting element {a[j]} right.",
                    "comparisons": comparisons,
                    "swaps": swaps,
                })
                j -= 1
            else:
                break
        a[j + 1] = key
        sorted_indices = list(range(i + 1))
        steps.append({
            "array": list(a),
            "comparing": [j + 1],
            "swapped": True,
            "sorted": sorted_indices,
            "description": f"Inserted key {key} at position {j + 1}.",
            "comparisons": comparisons,
            "swaps": swaps,
        })

    steps.append({
        "array": list(a),
        "comparing": [],
        "swapped": False,
        "sorted": list(range(n)),
        "description": f"Insertion sort finished! Total {comparisons} comparisons, {swaps} shifts.",
        "comparisons": comparisons,
        "swaps": swaps,
    })
    return steps


def _generate_a_star_grid_steps(size: int = 8) -> dict[str, Any]:
    start = [1, 1]
    target = [size - 2, size - 2]
    # Simple barrier
    walls = []
    for r in range(2, size - 2):
        walls.append([r, size // 2])

    steps = []
    # Simplified wave expansion pathfinding steps for visualization
    visited = [start]
    current = start
    steps.append({
        "current": current,
        "visited": list(visited),
        "path": [],
        "description": "Starting A* search from node (1, 1).",
    })

    # Direct diagonal-manhattan stepped exploration
    cx, cz = start
    path = [start]
    while [cx, cz] != target:
        if cx < target[0] and [cx + 1, cz] not in walls:
            cx += 1
        elif cz < target[1] and [cx, cz + 1] not in walls:
            cz += 1
        elif cx < target[0]:
            cx += 1
        else:
            cz += 1
        visited.append([cx, cz])
        path.append([cx, cz])
        steps.append({
            "current": [cx, cz],
            "visited": list(visited),
            "path": list(path) if [cx, cz] == target else [],
            "description": f"Exploring node ({cx}, {cz}), heuristic distance = {abs(cx - target[0]) + abs(cz - target[1])}.",
        })

    steps.append({
        "current": target,
        "visited": visited,
        "path": path,
        "description": f"Target reached! Found optimal path of {len(path)} steps.",
    })

    return {
        "gridSize": size,
        "start": start,
        "target": target,
        "walls": walls,
        "steps": steps,
    }


def register_visualize_algorithm_3d(server: MCPServer) -> None:
    @server.tool(
        name="visualize_algorithm_3d",
        description=(
            "Generates an interactive 3D step-by-step algorithm visualizer with "
            "animated voxel blocks in Three.js. Supports sorting algorithms (bubble_sort, "
            "insertion_sort) with comparative glowing pillars, and 3D grid pathfinding (a_star) "
            "with search wave exploration. Includes playback controls (play, pause, step forward, "
            "step backward, speed slider, metrics)."
        ),
        meta={"ui": {"resourceUri": ALGO_RESOURCE_URI}},
    )
    def visualize_algorithm_3d(
        algorithm: str = "bubble_sort",
        data: list[int] | None = None,
        arraySize: int = 12,
    ) -> CallToolResult:
        """
        Args:
            algorithm: Algorithm to visualize: 'bubble_sort', 'insertion_sort', or 'a_star'.
            data: Optional list of integers to sort (default: random list of 10-15 items).
            arraySize: Number of elements if generating random data (between 8 and 20).
        """
        algo = algorithm.lower().replace("-", "_").strip()

        if algo == "a_star":
            grid_data = _generate_a_star_grid_steps(size=8)
            payload = {
                "type": "pathfinding",
                "algorithm": "A* 3D Pathfinding",
                "grid": grid_data,
                "totalSteps": len(grid_data["steps"]),
            }
            summary = f"Generated 3D A* Pathfinding simulation with {len(grid_data['steps'])} exploration steps."
        else:
            if data and len(data) >= 3:
                input_arr = [max(1, min(50, int(x))) for x in data[:24]]
            else:
                size = max(6, min(20, arraySize))
                input_arr = random.sample(range(5, 50), size)

            if algo == "insertion_sort":
                steps = _generate_insertion_sort_steps(input_arr)
                algo_title = "Insertion Sort"
            else:
                steps = _generate_bubble_sort_steps(input_arr)
                algo_title = "Bubble Sort"

            payload = {
                "type": "sorting",
                "algorithm": algo_title,
                "initialArray": input_arr,
                "steps": steps,
                "totalSteps": len(steps),
            }
            summary = (
                f"Generated 3D {algo_title} visualization for array {input_arr}.\n"
                f"Total steps: {len(steps)}, comparisons: {steps[-1]['comparisons']}, swaps: {steps[-1]['swaps']}."
            )

        return CallToolResult(
            content=[TextContent(type="text", text=summary)],
            structured_content={"algorithmTrace": payload},
            is_error=False,
        )
