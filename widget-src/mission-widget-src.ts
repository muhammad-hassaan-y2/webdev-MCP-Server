import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";
import * as THREE from "three";

interface TestCase {
  input: unknown[];
  expected: unknown;
}
interface ParamSpec {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  unit?: string;
}
interface CodeMission {
  type: "code";
  id: string;
  title: string;
  concept: string;
  description: string;
  functionName: string;
  starterCode: string;
  tests: TestCase[];
}
interface SimulationMission {
  type: "simulation";
  id: string;
  title: string;
  concept: string;
  description: string;
  params: ParamSpec[];
  targetLabel: string;
}
type Mission = CodeMission | SimulationMission;

interface TestOutcome {
  input: unknown[];
  expected: unknown;
  actual: unknown;
  passed: boolean;
  error?: string;
}

let mission: Mission | null = null;
let studentId = "anonymous";
let app: App;

const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

function setStatus(text: string, tone: "" | "good" | "bad" = "") {
  const box = el("status");
  box.textContent = text;
  box.className = "status" + (tone ? " " + tone : "");
}

function renderHeader(m: Mission) {
  el("title").textContent = m.title;
  el("concept").textContent = m.concept;
  el("description").textContent = m.description;
  setStatus("");
  el("hint-box").textContent = "";
}

// ---------- Code mission UI ----------

function renderTestRows(tests: TestCase[], results: TestOutcome[] | null) {
  const list = el("tests");
  list.innerHTML = "";
  tests.forEach((t, i) => {
    const r = results?.[i];
    const row = document.createElement("div");
    row.className = "test-row " + (r ? (r.passed ? "pass" : "fail") : "pending");
    const label = `f(${t.input.map((x) => JSON.stringify(x)).join(", ")}) → expected ${JSON.stringify(t.expected)}`;
    const detail = r ? (r.error ? ` — error: ${r.error}` : ` — got ${JSON.stringify(r.actual)}`) : "";
    row.innerHTML = `<span class="dot"></span><span>${label}${detail}</span>`;
    list.appendChild(row);
  });
}

function buildCodeUI(m: CodeMission) {
  el("mission-body").innerHTML = `
    <textarea id="code" spellcheck="false"></textarea>
    <div class="actions">
      <button id="run-btn" class="primary">Run tests</button>
      <button id="hint-btn" class="secondary">Get a hint</button>
    </div>
    <div id="tests"></div>
  `;
  (el<HTMLTextAreaElement>("code")).value = m.starterCode;
  renderTestRows(m.tests, null);

  el("run-btn").addEventListener("click", async () => {
    setStatus("Running tests…");
    const code = (el<HTMLTextAreaElement>("code")).value;
    const result = await app.callServerTool({ name: "run_tests", arguments: { missionId: m.id, code } });
    const data = result.structuredContent as { allPassed: boolean; loadError: string | null; results: TestOutcome[] };
    renderTestRows(m.tests, data.results);

    if (data.loadError) {
      setStatus(data.loadError, "bad");
      return;
    }
    if (!data.allPassed) {
      setStatus("Not quite yet — some tests are still failing.", "bad");
      return;
    }

    setStatus("All tests passed locally — confirming with the server…");
    const rec = await app.callServerTool({
      name: "record_progress",
      arguments: { missionId: m.id, studentId, code },
    });
    const recData = rec.structuredContent as { allPassed: boolean; attempts: number };
    if (recData.allPassed) {
      setStatus("Verified server-side. Mission complete ✓", "good");
      await app.updateModelContext({
        content: [{ type: "text", text: `Student passed all tests for mission "${m.title}" (server-verified, attempt ${recData.attempts}).` }],
      });
    } else {
      setStatus("Server re-check didn't confirm this — try running again.", "bad");
    }
  });

  el("hint-btn").addEventListener("click", async () => {
    setStatus("Thinking of a hint…");
    const code = (el<HTMLTextAreaElement>("code")).value;
    const result = await app.callServerTool({ name: "get_hint", arguments: { missionId: m.id, code, attemptNumber: 1 } });
    const data = result.structuredContent as { hint: string };
    el("hint-box").textContent = data.hint;
    setStatus("");
  });
}

// ---------- Simulation mission UI ----------

interface Scene3D {
  renderer: THREE.WebGLRenderer;
  camera: THREE.PerspectiveCamera;
  scene: THREE.Scene;
  ball: THREE.Mesh;
  line: THREE.Line;
  animId: number | null;
}

function cssColor(varName: string, fallback: string): THREE.Color {
  const probe = document.createElement("div");
  probe.style.color = `var(${varName})`;
  document.body.appendChild(probe);
  const c = getComputedStyle(probe).color;
  document.body.removeChild(probe);
  const m = c.match(/\d+/g);
  if (!m) return new THREE.Color(fallback);
  return new THREE.Color(`rgb(${m[0]},${m[1]},${m[2]})`);
}

function initScene3D(canvas: HTMLCanvasElement): Scene3D {
  const wrap = canvas.parentElement as HTMLElement;
  const w = wrap.clientWidth || 560;
  const h = wrap.clientHeight || 220;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 300);
  camera.position.set(0, 14, 34);

  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const dir = new THREE.DirectionalLight(0xffffff, 0.6);
  dir.position.set(15, 25, 15);
  scene.add(dir);

  const groundMat = new THREE.MeshStandardMaterial({ color: cssColor("--surface-0", "#e6e5e0"), roughness: 1 });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(100, 50), groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(25, 0, 0);
  scene.add(ground);

  const padMat = new THREE.MeshStandardMaterial({ color: cssColor("--text-secondary", "#888") });
  const pad = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 0.4, 20), padMat);
  pad.position.set(0, 0.2, 0);
  scene.add(pad);

  const line = new THREE.Line(
    new THREE.BufferGeometry(),
    new THREE.LineBasicMaterial({ color: cssColor("--text-accent", "#378ADD") }),
  );
  scene.add(line);

  const ball = new THREE.Mesh(
    new THREE.SphereGeometry(0.7, 20, 20),
    new THREE.MeshStandardMaterial({ color: cssColor("--text-danger", "#D85A30") }),
  );
  ball.position.set(0, 0.7, 0);
  scene.add(ball);

  return { renderer, camera, scene, ball, line, animId: null };
}

function trajectoryPoints(angleDeg: number, velocity: number, steps: number) {
  const g = 9.8;
  const rad = (angleDeg * Math.PI) / 180;
  const range = (velocity ** 2 * Math.sin(2 * rad)) / g;
  const pts: THREE.Vector3[] = [];
  for (let i = 0; i <= steps; i++) {
    const x = (range * i) / steps;
    const y = Math.max(0, x * Math.tan(rad) - (g * x * x) / (2 * velocity * velocity * Math.cos(rad) ** 2));
    pts.push(new THREE.Vector3(x, y, 0));
  }
  return { pts, range };
}

function buildSimulationUI(m: SimulationMission) {
  const sliders = m.params
    .map(
      (p) => `
      <div class="param-row">
        <label><span>${p.label}</span><span id="val-${p.key}">${p.default}${p.unit ?? ""}</span></label>
        <input type="range" id="param-${p.key}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.default}">
      </div>`,
    )
    .join("");

  el("mission-body").innerHTML = `
    ${sliders}
    <div id="trajectory-wrap" style="width:100%; height:220px; border-radius:8px; overflow:hidden; background:var(--surface-1, #f5f7fa);">
      <canvas id="trajectory" style="width:100%; height:100%; display:block;"></canvas>
    </div>
    <div class="actions" style="justify-content:space-between; align-items:center;">
      <button id="launch-btn" class="secondary">Launch</button>
      <span style="font-size:13px; color:#666;">Actual range: <span id="actual-range">-</span> m</span>
    </div>
    <div class="answer-row">
      <input type="number" id="answer" placeholder="${m.targetLabel}">
      <button id="check-btn" class="primary">Check answer</button>
      <button id="hint-btn" class="secondary">Get a hint</button>
    </div>
  `;

  const currentParams: Record<string, number> = {};
  m.params.forEach((p) => (currentParams[p.key] = p.default));

  const canvas = el<HTMLCanvasElement>("trajectory");
  const s3d = initScene3D(canvas);

  const render = () => s3d.renderer.render(s3d.scene, s3d.camera);

  const redraw = () => {
    const { pts, range } = trajectoryPoints(currentParams["angle"] ?? 45, currentParams["velocity"] ?? 20, 48);
    s3d.line.geometry.setFromPoints(pts);
    s3d.ball.position.set(0, 0.7, 0);
    s3d.camera.lookAt(range / 2, 5, 0);
    el("actual-range").textContent = range.toFixed(2);
    render();
  };
  redraw();

  m.params.forEach((p) => {
    const input = el<HTMLInputElement>(`param-${p.key}`);
    input.addEventListener("input", () => {
      currentParams[p.key] = Number(input.value);
      el(`val-${p.key}`).textContent = `${input.value}${p.unit ?? ""}`;
      redraw();
    });
  });

  el("launch-btn").addEventListener("click", () => {
    if (s3d.animId) cancelAnimationFrame(s3d.animId);
    const { pts, range } = trajectoryPoints(currentParams["angle"] ?? 45, currentParams["velocity"] ?? 20, 90);
    let i = 0;
    const step = () => {
      if (i >= pts.length) {
        render();
        s3d.animId = null;
        return;
      }
      s3d.ball.position.set(pts[i].x, pts[i].y + 0.7, 0);
      s3d.camera.lookAt(range / 2, 5, 0);
      render();
      i++;
      s3d.animId = requestAnimationFrame(step);
    };
    step();
  });

  el("check-btn").addEventListener("click", async () => {
    const answerInput = el<HTMLInputElement>("answer");
    const studentAnswer = Number(answerInput.value);
    if (Number.isNaN(studentAnswer)) {
      setStatus("Type a number first.", "bad");
      return;
    }
    setStatus("Checking…");
    const result = await app.callServerTool({
      name: "check_simulation_answer",
      arguments: { missionId: m.id, params: currentParams, studentAnswer },
    });
    const data = result.structuredContent as { actual: number; passed: boolean };

    if (!data.passed) {
      setStatus(`Not quite — actual value is ${data.actual.toFixed(2)}. Try again.`, "bad");
      return;
    }

    setStatus("Correct locally — confirming with the server…");
    const rec = await app.callServerTool({
      name: "record_progress",
      arguments: { missionId: m.id, studentId, params: currentParams, studentAnswer },
    });
    const recData = rec.structuredContent as { allPassed: boolean; attempts: number };
    if (recData.allPassed) {
      setStatus("Verified server-side. Mission complete ✓", "good");
      await app.updateModelContext({
        content: [{ type: "text", text: `Student correctly predicted the result for mission "${m.title}" (server-verified, attempt ${recData.attempts}).` }],
      });
    } else {
      setStatus("Server re-check didn't confirm this — try again.", "bad");
    }
  });

  el("hint-btn").addEventListener("click", async () => {
    setStatus("Thinking of a hint…");
    const answerInput = el<HTMLInputElement>("answer");
    const studentAnswer = answerInput.value ? Number(answerInput.value) : undefined;
    const result = await app.callServerTool({
      name: "get_hint",
      arguments: { missionId: m.id, params: currentParams, studentAnswer, attemptNumber: 1 },
    });
    const data = result.structuredContent as { hint: string };
    el("hint-box").textContent = data.hint;
    setStatus("");
  });
}

// ---------- Boot ----------

function renderMission(m: Mission) {
  mission = m;
  renderHeader(m);
  if (m.type === "code") buildCodeUI(m);
  else buildSimulationUI(m);
}

async function init() {
  app = new App({ name: "tutor-widget", version: "1.0.0" }, {});

  app.ontoolresult = (params: any) => {
    const sc = params?.structuredContent;
    if (sc?.mission) {
      renderMission(sc.mission as Mission);
      if (sc.studentId) studentId = sc.studentId;
    }
  };

  await app.connect(new PostMessageTransport(window.parent, window.parent));
}

init();
