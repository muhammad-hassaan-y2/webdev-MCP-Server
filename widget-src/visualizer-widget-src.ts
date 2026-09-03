import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";
import * as THREE from "three";

// ────────────────────── Types ──────────────────────

interface AnimationSpec {
  type: "rotate" | "orbit" | "bounce" | "pulse" | "none";
  speed?: number;
  axis?: "x" | "y" | "z";
  orbitRadius?: number;
  orbitCenter?: [number, number, number];
}

interface SceneObject {
  type: "box" | "sphere" | "cylinder" | "torus" | "cone" | "ring" | "plane";
  position: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
  color: string;
  opacity?: number;
  label?: string;
  animation: AnimationSpec;
}

interface LightSpec {
  type: "ambient" | "directional" | "point";
  color: string;
  intensity: number;
  position?: [number, number, number];
}

interface SceneSpec {
  title: string;
  description: string;
  objects: SceneObject[];
  camera: { position: [number, number, number]; lookAt: [number, number, number] };
  lights: LightSpec[];
  gridHelper?: boolean;
  axesHelper?: boolean;
  backgroundColor?: string;
}

// ────────────────────── State ──────────────────────

let app: App;
let renderer: THREE.WebGLRenderer;
let camera: THREE.PerspectiveCamera;
let scene: THREE.Scene;
let animating = true;
let animId: number | null = null;

// For orbit-controls-like mouse interaction
let isDragging = false;
let prevMouse = { x: 0, y: 0 };
let spherical = { theta: 0, phi: Math.PI / 4, radius: 20 };
let lookAtTarget = new THREE.Vector3(0, 0, 0);

// For label hover
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const labeledMeshes: { mesh: THREE.Mesh; label: string }[] = [];

// For per-object animation state
interface AnimState {
  mesh: THREE.Mesh;
  spec: AnimationSpec;
  originalPos: THREE.Vector3;
  time: number;
}
const animStates: AnimState[] = [];

// ────────────────────── DOM ──────────────────────

const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

// ────────────────────── Scene Setup ──────────────────────

function createGeometry(type: string): THREE.BufferGeometry {
  switch (type) {
    case "sphere": return new THREE.SphereGeometry(1, 24, 24);
    case "cylinder": return new THREE.CylinderGeometry(1, 1, 2, 20);
    case "torus": return new THREE.TorusGeometry(1, 0.4, 16, 32);
    case "cone": return new THREE.ConeGeometry(1, 2, 20);
    case "ring": return new THREE.RingGeometry(0.5, 1, 32);
    case "plane": return new THREE.PlaneGeometry(2, 2);
    default: return new THREE.BoxGeometry(1, 1, 1);
  }
}

function buildScene(spec: SceneSpec) {
  const canvas = el<HTMLCanvasElement>("scene-canvas");
  const wrap = canvas.parentElement as HTMLElement;
  const w = wrap.clientWidth || 600;
  const h = 360;

  // Renderer
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  // Scene
  scene = new THREE.Scene();
  if (spec.backgroundColor) {
    scene.background = new THREE.Color(spec.backgroundColor);
  } else {
    scene.background = new THREE.Color("#1a1a2e");
  }

  // Camera
  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 500);
  const cp = spec.camera?.position || [10, 10, 10];
  const cl = spec.camera?.lookAt || [0, 0, 0];
  camera.position.set(cp[0], cp[1], cp[2]);
  lookAtTarget.set(cl[0], cl[1], cl[2]);
  camera.lookAt(lookAtTarget);

  // Initialize spherical coords from camera position
  const offset = new THREE.Vector3().subVectors(camera.position, lookAtTarget);
  spherical.radius = offset.length();
  spherical.theta = Math.atan2(offset.x, offset.z);
  spherical.phi = Math.acos(Math.max(-1, Math.min(1, offset.y / spherical.radius)));

  // Lights
  for (const light of spec.lights || []) {
    let l: THREE.Light;
    const color = new THREE.Color(light.color || "#ffffff");
    switch (light.type) {
      case "directional":
        l = new THREE.DirectionalLight(color, light.intensity ?? 0.8);
        if (light.position) (l as THREE.DirectionalLight).position.set(...light.position);
        break;
      case "point":
        l = new THREE.PointLight(color, light.intensity ?? 1, 100);
        if (light.position) (l as THREE.PointLight).position.set(...light.position);
        break;
      default:
        l = new THREE.AmbientLight(color, light.intensity ?? 0.5);
    }
    scene.add(l);
  }

  // Grid & Axes
  if (spec.gridHelper) scene.add(new THREE.GridHelper(40, 40, 0x444444, 0x222222));
  if (spec.axesHelper) scene.add(new THREE.AxesHelper(10));

  // Objects
  labeledMeshes.length = 0;
  animStates.length = 0;

  for (const obj of spec.objects) {
    const geo = createGeometry(obj.type);
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(obj.color || "#4a90d9"),
      transparent: (obj.opacity ?? 1) < 1,
      opacity: obj.opacity ?? 1,
      roughness: 0.5,
      metalness: 0.1,
    });
    const mesh = new THREE.Mesh(geo, mat);

    if (obj.position) mesh.position.set(...obj.position);
    if (obj.rotation) mesh.rotation.set(obj.rotation[0], obj.rotation[1], obj.rotation[2]);
    if (obj.scale) mesh.scale.set(...obj.scale);

    scene.add(mesh);

    if (obj.label) {
      labeledMeshes.push({ mesh, label: obj.label });
    }

    if (obj.animation && obj.animation.type !== "none") {
      animStates.push({
        mesh,
        spec: obj.animation,
        originalPos: mesh.position.clone(),
        time: 0,
      });
    }
  }

  // Header
  el("viz-title").textContent = spec.title || "3D Visualization";
  el("viz-description").textContent = spec.description || "";
  el("viz-loading").style.display = "none";

  // Start animation loop
  animate();
}

// ────────────────────── Animation Loop ──────────────────────

function animate() {
  if (!animating && animStates.length === 0) {
    renderer.render(scene, camera);
    return;
  }

  const dt = 0.016; // ~60fps

  for (const state of animStates) {
    if (!animating) break;
    state.time += dt;
    const speed = state.spec.speed ?? 1;

    switch (state.spec.type) {
      case "rotate": {
        const axis = state.spec.axis || "y";
        if (axis === "x") state.mesh.rotation.x += speed * dt;
        else if (axis === "z") state.mesh.rotation.z += speed * dt;
        else state.mesh.rotation.y += speed * dt;
        break;
      }
      case "orbit": {
        const r = state.spec.orbitRadius ?? 5;
        const center = state.spec.orbitCenter || [0, 0, 0];
        state.mesh.position.x = center[0] + r * Math.cos(state.time * speed);
        state.mesh.position.z = center[2] + r * Math.sin(state.time * speed);
        state.mesh.position.y = state.originalPos.y;
        break;
      }
      case "bounce": {
        state.mesh.position.y =
          state.originalPos.y + Math.abs(Math.sin(state.time * speed * 2)) * 2;
        break;
      }
      case "pulse": {
        const s = 1 + 0.2 * Math.sin(state.time * speed * 3);
        state.mesh.scale.set(s, s, s);
        break;
      }
    }
  }

  renderer.render(scene, camera);
  animId = requestAnimationFrame(animate);
}

// ────────────────────── Mouse Controls ──────────────────────

function setupControls(canvas: HTMLCanvasElement) {
  canvas.addEventListener("mousedown", (e) => {
    isDragging = true;
    prevMouse = { x: e.clientX, y: e.clientY };
  });

  canvas.addEventListener("mousemove", (e) => {
    // Hover labels
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    if (labeledMeshes.length > 0) {
      raycaster.setFromCamera(mouse, camera);
      const meshes = labeledMeshes.map((lm) => lm.mesh);
      const intersects = raycaster.intersectObjects(meshes);
      const tooltip = el("label-tooltip");
      if (intersects.length > 0) {
        const hit = labeledMeshes.find((lm) => lm.mesh === intersects[0].object);
        if (hit) {
          tooltip.textContent = hit.label;
          tooltip.style.display = "block";
          tooltip.style.left = e.clientX - rect.left + 10 + "px";
          tooltip.style.top = e.clientY - rect.top - 20 + "px";
        }
      } else {
        tooltip.style.display = "none";
      }
    }

    // Orbit dragging
    if (!isDragging) return;
    const dx = e.clientX - prevMouse.x;
    const dy = e.clientY - prevMouse.y;
    prevMouse = { x: e.clientX, y: e.clientY };

    spherical.theta -= dx * 0.01;
    spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy * 0.01));

    updateCameraFromSpherical();
  });

  canvas.addEventListener("mouseup", () => (isDragging = false));
  canvas.addEventListener("mouseleave", () => {
    isDragging = false;
    el("label-tooltip").style.display = "none";
  });

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    spherical.radius = Math.max(2, Math.min(100, spherical.radius + e.deltaY * 0.05));
    updateCameraFromSpherical();
  }, { passive: false });

  // Touch support
  canvas.addEventListener("touchstart", (e) => {
    if (e.touches.length === 1) {
      isDragging = true;
      prevMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  });
  canvas.addEventListener("touchmove", (e) => {
    if (!isDragging || e.touches.length !== 1) return;
    const dx = e.touches[0].clientX - prevMouse.x;
    const dy = e.touches[0].clientY - prevMouse.y;
    prevMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    spherical.theta -= dx * 0.01;
    spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy * 0.01));
    updateCameraFromSpherical();
  });
  canvas.addEventListener("touchend", () => (isDragging = false));
}

function updateCameraFromSpherical() {
  const x = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
  const y = spherical.radius * Math.cos(spherical.phi);
  const z = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
  camera.position.set(x + lookAtTarget.x, y + lookAtTarget.y, z + lookAtTarget.z);
  camera.lookAt(lookAtTarget);
}

// ────────────────────── Control Buttons ──────────────────────

function setupButtons(spec: SceneSpec) {
  el("reset-btn").addEventListener("click", () => {
    const cp = spec.camera?.position || [10, 10, 10];
    const cl = spec.camera?.lookAt || [0, 0, 0];
    lookAtTarget.set(cl[0], cl[1], cl[2]);
    camera.position.set(cp[0], cp[1], cp[2]);
    const offset = new THREE.Vector3().subVectors(camera.position, lookAtTarget);
    spherical.radius = offset.length();
    spherical.theta = Math.atan2(offset.x, offset.z);
    spherical.phi = Math.acos(Math.max(-1, Math.min(1, offset.y / spherical.radius)));
    camera.lookAt(lookAtTarget);
    renderer.render(scene, camera);
  });

  el("toggle-anim-btn").addEventListener("click", () => {
    animating = !animating;
    el("toggle-anim-btn").textContent = animating ? "Pause" : "Play";
    if (animating) animate();
  });
}

// ────────────────────── Boot ──────────────────────

async function init() {
  app = new App({ name: "visualizer-widget", version: "1.0.0" }, {});

  app.ontoolresult = (params: any) => {
    const sc = params?.structuredContent;
    if (sc?.scene) {
      const spec = sc.scene as SceneSpec;
      buildScene(spec);
      setupControls(el<HTMLCanvasElement>("scene-canvas"));
      setupButtons(spec);
    }
  };

  await app.connect(new PostMessageTransport(window.parent, window.parent));
}

init();
