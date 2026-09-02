# Interactive AI Tutor — MCP server (Python)

The Python rebuild of the tutor MCP server: same architecture, same trust
boundary, now on the official `mcp` Python SDK, with Gemini powering hints
and a real Three.js 3D scene for the physics mission instead of a flat
canvas.

**The one rule everything is built around**: the AI can propose a lesson or
a hint, but it can never decide the student passed. Only a deterministic
check — real code execution, real physics — can do that, and it's the only
thing allowed to write to the progress store.

## What's actually been verified

Everything below was checked by running a real server and sending it real
MCP JSON-RPC calls — not just written and assumed correct:

- Full MCP handshake, `tools/list`, `resources/read`, all 5 tools
- `start_mission` for both mission types, returning correct mission data
- `run_tests` catching the real off-by-one bug in the demo code mission
- `check_simulation_answer` computing the real projectile range
  (`v²sin(2θ)/g`) and rejecting wrong answers
- **`record_progress` refusing to mark a mission complete on wrong code or a
  wrong physics answer, and only recording completion once the real check
  passes** — this is the core trust boundary and it holds, for both mission
  types
- The project rebuilds from a **completely clean install** (`npm install` →
  `npm run build:widget` → fresh Python venv → `pip install -e .` → server
  start → all 5 tools present) — checked twice, once directly and once by
  precisely mirroring every step the Dockerfile runs (same file layout, same
  install command, same working directory) in a scratch directory to catch
  packaging-path bugs before they'd show up in a real container build

**One real limitation, stated plainly**: Docker itself isn't available in
the sandbox I built this in, so I could not run an actual `docker build`.
What I did instead — reproducing the Dockerfile's exact file layout and
install command by hand in a fresh venv and confirming the server starts
and every tool call works from that layout — is the closest verification
possible without Docker itself, and it did catch a real bug (see below).
Still, build the image yourself and sanity-check it before relying on it.

**A bug this process actually caught**: the first version of the Dockerfile
used a plain `pip install .`, which relocates the package into
site-packages and would have broken the widget's file lookup (it looks for
`widget-src/generated/mission-widget.html` relative to its own installed
location). Fixed to `pip install -e .`, which keeps the source tree where
the widget lookup expects it. This is exactly the kind of bug that looks
fine on a read-through and only shows up when something actually runs it.

## Project structure

```
mcp-tutor-py/
├── Dockerfile              # multi-stage: Node builds the widget, Python runs the server
├── pyproject.toml
├── package.json            # widget build tooling only - not needed at server runtime
├── .env.example
├── scripts/
│   └── build-widget.mjs    # bundles widget-src with esbuild into widget-src/generated/
├── widget-src/
│   ├── template.html
│   ├── mission-widget-src.ts   # client widget: code editor OR Three.js 3D scene, by mission type
│   └── generated/              # bundled output (not committed - build produces it)
└── src/tutor_mcp/
    ├── server.py            # entry point (mcp SDK's MCPServer, streamable-http transport)
    ├── missions/
    │   ├── types.py         # CodeMission / SimulationMission (pydantic, camelCase JSON)
    │   ├── off_by_one.py    # demo code mission
    │   ├── projectile_motion.py  # demo simulation mission
    │   └── registry.py
    ├── sandbox/
    │   ├── run_python.py    # deterministic code execution + grading
    │   └── physics.py       # deterministic simulation grading
    ├── store/
    │   └── progress_store.py    # JSON-file mastery store, written only by record_progress
    ├── tools/
    │   ├── start_mission.py
    │   ├── run_tests.py
    │   ├── check_simulation_answer.py
    │   ├── get_hint.py          # calls Gemini if GEMINI_API_KEY is set
    │   └── record_progress.py
    └── widget/
        ├── resource_uri.py
        └── register_resource.py # serves widget-src/generated/mission-widget.html

```

**Important convention**: every MCP tool function parameter is deliberately
named in camelCase (`missionId`, not `mission_id`), matching the JSON keys
sent over the wire. The `mcp` SDK builds its input schema straight from
Python parameter names with no automatic aliasing, so snake_case parameters
here would silently reject every real call — this bit me once already
during development (see above), which is exactly why it's called out.

## Requirements

- Python 3.10+
- Node.js 20+ and npm — **build-time only**, to bundle the widget. Not
  needed to run the server itself once `widget-src/generated/` exists.
- Python 3 is also needed at server *runtime*, separately from the above —
  code missions shell out to `python3` to run student code.

## Run it locally

```bash
# one-time: build the widget
npm install
npm run build:widget

# python side
python3 -m venv .venv
./.venv/bin/pip install -e .
cp .env.example .env   # fill in GEMINI_API_KEY if you want AI-generated hints
./.venv/bin/python -m tutor_mcp.server
```

Server listens on `http://localhost:3000/mcp`. Works fine with no
`GEMINI_API_KEY` set — `get_hint` just falls back to each mission's static
hints instead of calling Gemini.

## Test it yourself, no ChatGPT/Claude needed

Same commands I used to verify all of the above:

```bash
# 1. initialize and capture the session id from the response headers
curl -s -D - -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'

SID="paste-the-mcp-session-id-header-value-here"

curl -s -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"start_mission","arguments":{"missionId":"projectile-range","studentId":"me"}}}'

curl -s -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"check_simulation_answer","arguments":{"missionId":"projectile-range","params":{"angle":45,"velocity":20},"studentAnswer":40.8}}}'
```

## Deploy it

The included `Dockerfile` builds the widget (Node stage) and runs the
server (Python stage) — works on Render, Fly.io, Railway, Google Cloud Run,
or a plain VPS with Docker. As noted above, I couldn't run the actual
`docker build` in the environment I wrote this in, only a careful hand
simulation of it — build and test the image yourself before trusting it in
production, the same way you should for anything pulled from a chat.

Before pointing this at real students:

- **Add auth.** No authentication exists on `/mcp` right now. At minimum a
  shared-secret header; for real multi-user use, OAuth (the SDK supports it).
- **Harden the code sandbox.** `run_python.py` runs student code as a plain
  subprocess with a timeout and Python's isolated mode (`-I`) — reasonable
  for a demo, not a real multi-tenant sandbox. Use something actually
  isolated for production (a disposable container with `--network=none`,
  gVisor, Firecracker, nsjail).
- **Swap the progress store.** `progress_store.py` is a flat JSON file with
  a simple in-process lock — fine for a demo, not for concurrent real users.
  Move to Postgres/SQLite.

## Connect it to ChatGPT

1. Deploy so `https://your-domain/mcp` is publicly reachable.
2. In ChatGPT, enable Developer mode (currently under Security and login →
   Developer mode / Plugins - this has moved before and may move again,
   check ChatGPT's help center if it's not there).
3. Add a new connector, paste in your `/mcp` URL.
4. Be explicit the first few times — *"Use the interactive-tutor connector
   to start the projectile-range mission for me"* — models don't always
   reach for a custom tool unprompted.

This personal-connector path works immediately, for your own account, no
review needed. Making it installable by other people as a listed app is a
separate, slower path through OpenAI's Apps SDK review process.

## Connect it to Claude

Same idea: add a custom connector in Claude's settings, paste the same
`/mcp` URL. The widget is built against the shared MCP Apps extension
(`@modelcontextprotocol/ext-apps`), not a ChatGPT-only API, so the same
server works in both places without separate code.

## Adding a mission

- **Code mission**: add a `CodeMission` to `src/tutor_mcp/missions/`
  (function name, starter code, tests), register it in `registry.py`. No
  other changes needed.
- **Simulation mission**: add a `SimulationMission` with its `params`, then
  a matching formula function in `sandbox/physics.py` keyed by the mission
  id. The widget already branches on `mission.type` and reuses the same
  Three.js scene machinery — you'd extend the drawing logic in
  `widget-src/mission-widget-src.ts` if the new mission needs a visibly
  different 3D scene (not just different numbers going into the same
  launcher-and-trajectory shape).
