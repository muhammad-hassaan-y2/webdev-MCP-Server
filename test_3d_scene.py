import httpx, json

c = httpx.Client(base_url="http://localhost:3000")
r = c.post("/mcp", json={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1.0"}}}, headers={"Accept":"application/json, text/event-stream"})
sid = r.headers.get("mcp-session-id")
h = {"Accept": "application/json, text/event-stream", "Mcp-Session-Id": sid}

sr = c.post("/mcp", json={"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"generate_3d_scene","arguments":{"query":"a solar system with sun and planets"}}}, headers=h)
sd = [l for l in sr.text.splitlines() if l.startswith("data:")][0][5:]
result = json.loads(sd)
text = result["result"]["content"][0]["text"]
print("Text:", text)
sc = result["result"]["structuredContent"]["scene"]
print("Title:", sc["title"])
print("Objects:", len(sc["objects"]))
for o in sc["objects"]:
    anim = o.get("animation", {}).get("type", "none")
    label = o.get("label", "")
    print(f"  - {o['type']} label={label} anim={anim}")
