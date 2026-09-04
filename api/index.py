import os
import sys

# Ensure src directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Vercel serverless has a read-only filesystem except /tmp
os.environ["TUTOR_DATA_DIR"] = "/tmp/.data"

from tutor_mcp.server import build_server

# Build the MCP server
server = build_server()

# Export Starlette ASGI application for Vercel serverless runtime
app = server.streamable_http_app()
