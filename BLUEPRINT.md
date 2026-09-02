# Blueprint: interactive AI tutor platform (Python edition)

This is the design document. `README.md` covers how to run and deploy the
working code — this file covers the bigger picture: why it's built this
way, the full tool catalog, and what to build next.

## The core principle, stated once and enforced everywhere

**The AI proposes. A deterministic engine decides.** The model (Gemini for
hints, or whichever model sits inside the host you connect to - ChatGPT's
or Claude's) is good at interpreting what a student is confused about,
picking a relevant mission, and phrasing a hint. It is not the thing that
gets to decide the student got the right answer. That decision is made by
actually running code, actually computing physics — and it's made *inside
your server*, not by trusting whatever the conversation says.

This matters concretely because of where this system lives: when a student
connects through ChatGPT, you don't control ChatGPT's model or its system
prompt. You only control what your tools accept and return. So the
correctness rule can never be "trust the model's claim" — it has to be
"the progress store only writes when the deterministic check, run again,
server-side, says pass." That's exactly what `record_progress` does, for
both mission types, and it's the one piece of this system that should
never be relaxed - regardless of which language the server is written in
or which model is generating hints.

## System architecture

```
 Student
    |
    v
 Host LLM  (ChatGPT or Claude - reads intent, decides which tool to call)
    |
    v
 Your MCP server (Python, mcp SDK) --------------------------
 |                                                            |
 |  Strategist (Gemini)            Deterministic engine       |
 |  - picks/starts a mission        - runs student code       |
 |  - writes hints                  - computes real physics   |
 |  - never grades anything         - the ONLY thing that     |
 |        \                             grades                |
 |         \                        /                         |
 |          v                      v                          |
 |              Progress store (written only by the engine)   |
 --------------------------------------------------------------
    |
    v
 Widget rendered back in the same chat (MCP Apps: code editor
 or a real Three.js 3D scene, depending on mission type)
```

## What's built right now

Two mission types, sharing one server, one progress store, and one widget
codebase that branches by mission type:

| Mission type | Example | Student interacts with | Deterministic check |
|---|---|---|---|
| `code` | `off-by-one-sum` | Editable code, "run tests" | Real Python execution against fixed test cases |
| `simulation` | `projectile-range` | Sliders + a real 3D Three.js scene (launcher, trajectory arc, animated launch), numeric prediction | Real physics formula computed server-side |

Five tools: `start_mission`, `run_tests`, `check_simulation_answer`,
`get_hint`, `record_progress`. See `README.md` for exact schemas.

## Why Python for the server, and what stays JavaScript regardless

The MCP protocol itself is language-agnostic - tools, resources, and the
`_meta.ui.resourceUri` linking mechanism are just JSON over HTTP. That's
what makes this split possible:

- **Server (Python)**: tool logic, deterministic validators, progress
  store. Chosen here for direct access to Python's scientific stack
  (`numpy`/`scipy`/`sympy` for future math/ML missions) without any FFI or
  subprocess bridging.
- **Widget (always JavaScript/WebGL)**: this doesn't change no matter what
  the server is written in, because it runs inside the student's browser,
  inside the MCP host's iframe. The Three.js 3D scene, the code editor -
  all of it is `widget-src/mission-widget-src.ts`, bundled once at build
  time, served as a static string by the Python server. Python never
  touches WebGL; it just hands over pre-built HTML.

If you ever wanted to go back to a Node-based server, only the `src/`
directory changes - `widget-src/` is untouched, since it was never
language-coupled to begin with.

## Extending to more domains (math, ML, robotics)

The `simulation` mission type generalizes past physics. The pattern is
always: **params the student controls -> a 3D or 2D scene that visualizes
the effect -> a server-side formula that's the ground truth.**

- **Math**: student picks coefficients of a quadratic, widget graphs it in
  the same Three.js canvas (or a simpler 2D plot), predicts the roots;
  checker uses the quadratic formula, or `sympy` (via the same subprocess
  pattern `run_python.py` already uses) if you want to check algebraic
  *steps*, not just a final number.
- **ML**: student picks a learning rate and starting point on a loss curve;
  checker recomputes the same gradient descent with real `numpy` and
  compares final loss or step count. This is a natural fit for the Python
  server specifically - no subprocess needed, just import numpy directly.
- **Robotics**: student picks joint angles for a simple 2-link arm; Three.js
  renders the arm in 3D; checker computes real forward kinematics
  (`x = l1*cos(θ1) + l2*cos(θ1+θ2)`, etc.) server-side.

None of these need new architecture - a new mission entry, a new formula
function in `sandbox/physics.py`, and (for a visibly different scene) more
drawing logic in `mission-widget-src.ts` following the existing Three.js
scene setup for the projectile mission.

## Tool catalog - current and planned

Current:

- `start_mission(missionId, studentId)` - begins a mission, links the widget
- `run_tests(missionId, code)` - deterministic grading for code missions
- `check_simulation_answer(missionId, params, studentAnswer)` -
  deterministic grading for simulation missions
- `get_hint(missionId, code?, params?, studentAnswer?, attemptNumber)` -
  Gemini-generated hint, always grounded in a real result computed first
- `record_progress(...)` - the only writer of mastery state; re-validates
  server-side regardless of what it's told

Worth adding next:

1. **`list_missions()`** - exposes `registry.list_missions()` as a tool so
   the host model can browse what's available instead of you hardcoding
   mission ids into prompts.
2. **`get_student_progress(studentId)`** - exposes `progress_store.get_progress()`
   so the strategist can personalize: "you've already got off-by-one-sum,
   want something harder?"

## Before this touches real students

- **Auth.** No authentication exists on the demo endpoint. Add at least a
  shared secret, ideally OAuth, before deploying anywhere reachable.
- **Sandbox isolation.** The code-execution sandbox is a bare subprocess
  with a timeout - fine for a demo, not safe for arbitrary students at
  scale.
- **Real database.** The JSON-file progress store uses a simple in-process
  lock, which doesn't help across multiple server instances/processes.
  Swap for Postgres/SQLite before real concurrent use.
- **Reach.** Distributing this purely as a ChatGPT/Claude connector limits
  your audience to people who already have one of those apps and know how
  to add a connector. Worth naming honestly if the goal is reaching
  students who don't already have that access.

## Suggested build order from here

1. Add `list_missions` and `get_student_progress` (small, high leverage).
2. Add one more mission per domain you care about (math/ML/robotics above)
   to prove the pattern holds beyond physics.
3. Add auth and swap the progress store for a real database.
4. Actually run `docker build` yourself and confirm it works end-to-end -
   I verified the file-layout logic by hand-simulating every Dockerfile
   step, but Docker itself wasn't available where I built this, so the
   actual image build is the one thing you should check before trusting it.
5. Deploy, connect it to your own ChatGPT/Claude account, and actually use
   it yourself for a week before showing anyone else.
