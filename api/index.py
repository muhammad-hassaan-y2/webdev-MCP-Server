import os
import sys
import json
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, Response

# Ensure src directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Vercel serverless has a read-only filesystem except /tmp
os.environ["TUTOR_DATA_DIR"] = "/tmp/.data"

from tutor_mcp.server import build_server

# Build the MCP server instance
mcp_server = build_server()

async def handle_home(request: Request):
    tools = await mcp_server.list_tools()
    resources = await mcp_server.list_resources()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Omni Tutor MCP • Production Vercel Server</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #050810; color: #f8fafc; margin: 0; padding: 40px 20px; }}
    .container {{ max-width: 860px; margin: 0 auto; }}
    .badge {{ display: inline-block; background: rgba(52, 211, 153, 0.15); border: 1px solid #10b981; color: #34d399; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
    h1 {{ font-size: 32px; font-weight: 800; margin: 16px 0 8px; background: linear-gradient(135deg, #38bdf8, #a855f7, #f43f5e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    p.subtitle {{ color: #94a3b8; font-size: 15px; margin-bottom: 28px; }}
    .card {{ background: #0d1424; border: 1px solid #1e2d4b; border-radius: 14px; padding: 22px; margin-bottom: 22px; }}
    .card h2 {{ margin-top: 0; font-size: 18px; color: #38bdf8; }}
    .endpoint {{ background: #060913; border: 1px solid #334155; padding: 12px 16px; border-radius: 8px; font-family: monospace; font-size: 14px; color: #38bdf8; display: flex; justify-content: space-between; align-items: center; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .item {{ background: #070c18; border: 1px solid #1e293b; padding: 12px 14px; border-radius: 8px; font-size: 13px; }}
    .item-title {{ font-weight: 700; color: #f8fafc; margin-bottom: 4px; }}
    .item-desc {{ color: #94a3b8; font-size: 11px; }}
    pre {{ background: #060913; padding: 14px; border-radius: 8px; font-size: 12px; color: #a5b4fc; overflow-x: auto; }}
  </style>
</head>
<body>
  <div class="container">
    <span class="badge">● Online • Production Live</span>
    <h1>Omni Tutor MCP</h1>
    <p class="subtitle">Multi-Sensory 3D Generative UI STEM & Coding Studio for Model Context Protocol</p>
    
    <div class="card">
      <h2>🔌 Connect to this MCP Server</h2>
      <div class="endpoint">
        <span>https://mcp-tutor-py.vercel.app/mcp</span>
      </div>
      <p style="font-size: 12px; color: #94a3b8; margin-top: 10px;">Transport: Streamable HTTP (JSON-RPC 2.0). Connect via Claude Desktop, ChatGPT, or any MCP client.</p>
    </div>

    <div class="card">
      <h2>⚙️ Claude Desktop Configuration</h2>
      <pre>{{
  "mcpServers": {{
    "omni-tutor": {{
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-tutor-py.vercel.app/mcp"]
    }}
  }}
}}</pre>
    </div>

    <div class="card">
      <h2>🛠️ Registered Tools ({len(tools)} Production Tools)</h2>
      <div class="grid">
        {"".join(f'<div class="item"><div class="item-title">{t.name}</div><div class="item-desc">{t.description[:80]}...</div></div>' for t in tools)}
      </div>
    </div>

    <div class="card">
      <h2>🎨 Generative UI Widgets ({len(resources)} Resources)</h2>
      <div class="grid">
        {"".join(f'<div class="item"><div class="item-title" style="color:#a855f7;">{r.name}</div><div class="item-desc">{r.uri}</div></div>' for r in resources)}
      </div>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(html)

async def handle_mcp(request: Request):
    if request.method == "OPTIONS":
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    
    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    # Handle notifications
    if method == "notifications/initialized":
        return Response(status_code=204, headers={"Access-Control-Allow-Origin": "*"})

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
                headers={"Access-Control-Allow-Origin": "*"}
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
                headers={"Access-Control-Allow-Origin": "*"}
            )
    else:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": req_id},
            status_code=404,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    return JSONResponse(
        {"jsonrpc": "2.0", "result": result, "id": req_id},
        headers={"Access-Control-Allow-Origin": "*"}
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
            response = await handle_home(request)
        else:
            response = await handle_mcp(request)
        await response(scope, receive, send)
