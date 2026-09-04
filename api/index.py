import os
import sys
import json
import mimetypes
from pathlib import Path
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, Response

# Ensure src directory is on sys.path
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Vercel serverless has a read-only filesystem except /tmp
os.environ["TUTOR_DATA_DIR"] = "/tmp/.data"

from tutor_mcp.server import build_server

# Build the MCP server instance
mcp_server = build_server()

WEBMCP_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Link": '<https://mcp-tutor-py.vercel.app/mcp>; rel="mcp-server"',
    "X-MCP-Endpoint": "https://mcp-tutor-py.vercel.app/mcp",
}

async def handle_get(request: Request):
    path_str = request.url.path.strip("/")
    
    # Root, dashboard, or Vercel internal rewritten entrypoint -> serve interactive WebMCP Studio
    if not path_str or path_str in ("dashboard", "index.html", "api/index.py", "api/index", "api"):
        dash_path = BASE_DIR / "test_dashboard.html"
        if dash_path.exists():
            return HTMLResponse(dash_path.read_text(encoding="utf-8"), headers=WEBMCP_HEADERS)

    # Check if a static demo or widget file is requested
    target_file = BASE_DIR / path_str
    if target_file.exists() and target_file.is_file() and not path_str.endswith(".py"):
        mime, _ = mimetypes.guess_type(str(target_file))
        mime = mime or "text/html"
        try:
            content = target_file.read_text(encoding="utf-8")
            return Response(content, media_type=mime, headers=WEBMCP_HEADERS)
        except UnicodeDecodeError:
            content_b = target_file.read_bytes()
            return Response(content_b, media_type=mime, headers=WEBMCP_HEADERS)

    # Fallback to home dashboard
    dash_path = BASE_DIR / "test_dashboard.html"
    return HTMLResponse(dash_path.read_text(encoding="utf-8"), headers=WEBMCP_HEADERS)

async def handle_mcp(request: Request):
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=WEBMCP_HEADERS)
        
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400,
            headers=WEBMCP_HEADERS
        )
    
    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    # Handle notifications
    if method == "notifications/initialized":
        return Response(status_code=204, headers=WEBMCP_HEADERS)

    if method == "initialize":
        result = {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False}
            },
            "serverInfo": {
                "name": "omni-tutor",
                "version": "1.0.0"
            }
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        tools = await mcp_server.list_tools()
        result = {"tools": [t.model_dump() for t in tools]}
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        try:
            call_res = await mcp_server.call_tool(name, args)
            content_list = []
            for c in call_res.content:
                if hasattr(c, "text"):
                    content_list.append({"type": "text", "text": c.text})
                elif hasattr(c, "data"):
                    content_list.append({"type": "image", "data": c.data, "mimeType": getattr(c, "mime_type", "image/png")})
            result = {
                "content": content_list,
                "isError": getattr(call_res, "is_error", False)
            }
        except Exception as e:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"}, "id": req_id},
                status_code=500,
                headers=WEBMCP_HEADERS
            )
    elif method == "resources/list":
        resources = await mcp_server.list_resources()
        result = {"resources": [r.model_dump() for r in resources]}
    elif method == "resources/read":
        uri = params.get("uri")
        try:
            r_res = await mcp_server.read_resource(uri)
            result = {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": getattr(c, "mime_type", "text/html"),
                        "text": getattr(c, "content", "")
                    }
                    for c in r_res
                ]
            }
        except Exception as e:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Resource read failed: {str(e)}"}, "id": req_id},
                status_code=500,
                headers=WEBMCP_HEADERS
            )
    else:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": req_id},
            status_code=404,
            headers=WEBMCP_HEADERS
        )

    return JSONResponse(
        {"jsonrpc": "2.0", "result": result, "id": req_id},
        headers=WEBMCP_HEADERS
    )

async def app(scope, receive, send):
    """Universal ASGI handler for Vercel Serverless Function."""
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                break
        return

    if scope["type"] == "http":
        request = Request(scope, receive)
        if request.method == "GET":
            response = await handle_get(request)
        else:
            response = await handle_mcp(request)
        await response(scope, receive, send)
