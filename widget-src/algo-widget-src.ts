import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";
import * as THREE from "three";

interface SortingStep {
  array: number[];
  comparing: number[];
  swapped: boolean;
  sorted: number[];
  description: string;
  comparisons: number;
  swaps: number;
}

interface AlgorithmTrace {
  type: "sorting" | "pathfinding";
  algorithm: string;
  initialArray?: number[];
  steps: SortingStep[];
  totalSteps: number;
}

let app: App;
let renderer: THREE.WebGLRenderer;
let camera: THREE.PerspectiveCamera;
let scene: THREE.Scene;
let trace: AlgorithmTrace | null = null;
let currentStepIdx = 0;
let isPlaying = false;
let playInterval: any = null;
let playbackSpeedMs = 400;

// Mouse controls
let isDragging = false;
let prevMouse = { x: 0, y: 0 };
let spherical = { theta: 0.3, phi: Math.PI / 3, radius: 24 };
const lookAtTarget = new THREE.Vector3(0, 5, 0);

// Visual Meshes
const pillarMeshes: THREE.Mesh[] = [];

const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

function initScene() {
  const canvas = el<HTMLCanvasElement>("algo-canvas");
  const wrap = canvas.parentElement as HTMLElement;
  const w = wrap.clientWidth || 600;
  const h = 320;

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  scene = new THREE.Scene();
  scene.background = new THREE.Color("#080c14");

  camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 200);
  updateCameraPosition();

  // Lights
  const ambient = new THREE.AmbientLight(0xffffff, 0.7);
  scene.add(ambient);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(15, 25, 20);
  scene.add(dirLight);

  const grid = new THREE.GridHelper(30, 30, 0x1e293b, 0x0f172a);
  grid.position.y = 0;
  scene.add(grid);

  setupMouseControls(canvas);
  animate();
}

function updateCameraPosition() {
  const x = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
  const y = spherical.radius * Math.cos(spherical.phi);
  const z = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
  camera.position.set(x, y, z);
  camera.lookAt(lookAtTarget);
}

function setupMouseControls(canvas: HTMLCanvasElement) {
  canvas.addEventListener("mousedown", (e) => {
    isDragging = true;
    prevMouse = { x: e.clientX, y: e.clientY };
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const dx = e.clientX - prevMouse.x;
    const dy = e.clientY - prevMouse.y;
    prevMouse = { x: e.clientX, y: e.clientY };

    spherical.theta -= dx * 0.01;
    spherical.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05, spherical.phi + dy * 0.01));
    updateCameraPosition();
  });

  window.addEventListener("mouseup", () => (isDragging = false));

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    spherical.radius = Math.max(10, Math.min(50, spherical.radius + e.deltaY * 0.05));
    updateCameraPosition();
  }, { passive: false });
}

function renderPillars(step: SortingStep) {
  const arr = step.array;
  const n = arr.length;
  const spacing = 1.4;
  const startX = -((n - 1) * spacing) / 2;

  // Clear existing pillars if count changed
  if (pillarMeshes.length !== n) {
    pillarMeshes.forEach((m) => scene.remove(m));
    pillarMeshes.length = 0;

    for (let i = 0; i < n; i++) {
      const geo = new THREE.BoxGeometry(1.0, 1.0, 1.0);
      const mat = new THREE.MeshStandardMaterial({
        color: new THREE.Color("#3b82f6"),
        roughness: 0.3,
        metalness: 0.2,
      });
      const mesh = new THREE.Mesh(geo, mat);
      scene.add(mesh);
      pillarMeshes.push(mesh);
    }
  }

  // Update pillar heights, positions, colors
  for (let i = 0; i < n; i++) {
    const mesh = pillarMeshes[i];
    const val = arr[i];
    const h = Math.max(0.5, val * 0.35);

    mesh.scale.set(1.0, h, 1.0);
    mesh.position.set(startX + i * spacing, h / 2, 0);

    const mat = mesh.material as THREE.MeshStandardMaterial;
    if (step.comparing.includes(i)) {
      mat.color.set(step.swapped ? "#ef4444" : "#f59e0b");
      mat.emissive.set(step.swapped ? "#7f1d1d" : "#78350f");
    } else if (step.sorted.includes(i)) {
      mat.color.set("#10b981");
      mat.emissive.set("#064e3b");
    } else {
      mat.color.set("#3b82f6");
      mat.emissive.set("#1e3a8a");
    }
  }

  // Update UI narrative and badges
  el("badge-step").textContent = `Step: ${currentStepIdx + 1} / ${trace?.totalSteps || 0}`;
  el("badge-comparisons").textContent = `Comparisons: ${step.comparisons || 0}`;
  el("badge-swaps").textContent = `Swaps: ${step.swaps || 0}`;
  el("step-narrative").textContent = step.description;
}

function showStep(idx: number) {
  if (!trace || !trace.steps || trace.steps.length === 0) return;
  currentStepIdx = Math.max(0, Math.min(trace.steps.length - 1, idx));
  renderPillars(trace.steps[currentStepIdx]);

  if (currentStepIdx >= trace.steps.length - 1 && isPlaying) {
    pause();
  }
}

function play() {
  if (isPlaying) return;
  if (currentStepIdx >= (trace?.steps.length || 1) - 1) {
    currentStepIdx = 0;
  }
  isPlaying = true;
  el("btn-play").textContent = "⏸️ Pause";
  el("btn-play").classList.remove("primary");

  playInterval = setInterval(() => {
    if (currentStepIdx < (trace?.steps.length || 1) - 1) {
      showStep(currentStepIdx + 1);
    } else {
      pause();
    }
  }, playbackSpeedMs);
}

function pause() {
  isPlaying = false;
  clearInterval(playInterval);
  el("btn-play").textContent = "▶️ Play";
  el("btn-play").classList.add("primary");
}

function setupControls() {
  el("btn-play").addEventListener("click", () => {
    if (isPlaying) pause();
    else play();
  });

  el("btn-next").addEventListener("click", () => {
    pause();
    showStep(currentStepIdx + 1);
  });

  el("btn-prev").addEventListener("click", () => {
    pause();
    showStep(currentStepIdx - 1);
  });

  el("btn-reset").addEventListener("click", () => {
    pause();
    showStep(0);
  });

  const speedBtn = el("btn-speed");
  speedBtn.addEventListener("click", () => {
    if (playbackSpeedMs === 400) {
      playbackSpeedMs = 200;
      speedBtn.textContent = "2x";
    } else if (playbackSpeedMs === 200) {
      playbackSpeedMs = 80;
      speedBtn.textContent = "4x";
    } else {
      playbackSpeedMs = 400;
      speedBtn.textContent = "1x";
    }
    if (isPlaying) {
      pause();
      play();
    }
  });
}

function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}

async function init() {
  initScene();
  setupControls();

  app = new App({ name: "algo-widget", version: "1.0.0" }, {});

  app.ontoolresult = (params: any) => {
    const sc = params?.structuredContent;
    if (sc?.algorithmTrace) {
      trace = sc.algorithmTrace as AlgorithmTrace;
      el("algo-title").textContent = `3D ${trace.algorithm} Simulation`;
      el("algo-subtitle").textContent = `${trace.totalSteps} steps computed deterministically.`;
      showStep(0);
    }
  };

  await app.connect(new PostMessageTransport(window.parent, window.parent));
}

init();
