import subprocess
import sys
import tempfile
import time
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent


def register_run_code_scratchpad(server: MCPServer) -> None:
    @server.tool(
        name="run_code_scratchpad",
        description=(
            "Executes an arbitrary Python code snippet in a safe, isolated "
            "subprocess with a 5-second timeout. Captures standard output, "
            "standard error, exit code, and execution time. Use this when you "
            "or the student need to run exploratory code, test a calculation, "
            "or verify a Python concept outside of a fixed mission."
        ),
    )
    def run_code_scratchpad(code: str) -> CallToolResult:
        """
        Args:
            code: The Python source code to execute.
        """
        if not code.strip():
            return CallToolResult(
                content=[TextContent(type="text", text="Error: Code snippet cannot be empty.")],
                structured_content={"success": False, "stdout": "", "stderr": "Empty code snippet", "exitCode": 1, "executionTimeMs": 0},
                is_error=True,
            )

        python_bin = sys.executable or "python3"
        start_time = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="scratchpad-") as tmpdir:
            script_file = Path(tmpdir) / "scratchpad.py"
            script_file.write_text(code, encoding="utf-8")

            try:
                proc = subprocess.run(
                    [python_bin, "-I", str(script_file)],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                )
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                success = proc.returncode == 0
                stdout = proc.stdout.strip()
                stderr = proc.stderr.strip()
                exit_code = proc.returncode

                output_text = stdout if stdout else ("(No output printed)" if success else stderr)
                summary = (
                    f"Execution completed in {duration_ms}ms (exit code {exit_code}):\n\n{output_text}"
                )

                return CallToolResult(
                    content=[TextContent(type="text", text=summary)],
                    structured_content={
                        "success": success,
                        "stdout": stdout,
                        "stderr": stderr,
                        "exitCode": exit_code,
                        "executionTimeMs": duration_ms,
                    },
                    is_error=not success,
                )

            except subprocess.TimeoutExpired:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Execution timed out after 5.0 seconds (possible infinite loop).")],
                    structured_content={
                        "success": False,
                        "stdout": "",
                        "stderr": "Execution timed out after 5.0 seconds.",
                        "exitCode": -1,
                        "executionTimeMs": duration_ms,
                    },
                    is_error=True,
                )
