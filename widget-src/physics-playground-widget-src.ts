import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";
import * as THREE from "three";
import * as CANNON from "cannon-es";

interface ObjectDef {
  type: "box" | "sphere";
  size?: [number, number, number];
  radius?: number;
  position: [number, number, number];
  rotation?: [number, number, number];
  velocity?: [number, number, number];
  mass: number;
  color: string;
}

interface PhysicsWorldSpec {
  title: string;
  description: string;
  sceneType: string;
  gravity: number;
  restitution: number;
  friction: number;
  objects: ObjectDef[];
}

let app: App;
let renderer: THREE.WebGLRenderer;
let camera: THREE.PerspectiveCamera;
let scene: THREE.Scene;
let world: CANNON.World;
let defaultMaterial: CANNON.Material;

interface BodyMeshPair {
  mesh: THREE.Mesh;
  body: CANNON.Body;
}
let pairs: BodyMeshPair[] = [];
let currentSpec: PhysicsWorldSpec | null = null;

// Camera orbit
let isDragging = false;
let prevMouse = { x: 0, y: 0 };
let spherical = { theta: 0.4, phi: Math.PI / 3.2, radius: 26 };
const lookAtTarget = new THREE.Vector3(0, 3, 0);

// Raycaster for shooting
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

function initThree() {
  const canvas = el<HTMLCanvasElement>("physics-canvas");
  const wrap = canvas.parentElement as HTMLElement;
  const w = wrap.clientWidth || 600;
  const h = 340;

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  scene = new THREE.Scene();
  scene.background = new THREE.Color("#050811");

  camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 200);
  updateCamera();

  // Lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dir = new THREE.DirectionalLight(0xffffff, 0.8);
  dir.position.set(20, 35, 20);
  scene.add(dir);

  // Ground Grid
  const grid = new THREE.GridHelper(40, 40, 0x1e293b, 0x0f172a);
  grid.position.y = 0;
  scene.add(grid);

  setupControls(canvas);
}

function updateCamera() {
  const x = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
  const y = spherical.radius * Math.cos(spherical.phi);
  const z = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
  camera.position.set(x + lookAtTarget.x, y + lookAtTarget.y, z + lookAtTarget.z);
  camera.lookAt(lookAtTarget);
}

function initCannon(gravity: number, restitution: number, friction: number) {
  world = new CANNON.World();
  world.gravity.set(0, gravity, 0);

  defaultMaterial = new CANNON.Material("default");
  const contactMat = new CANNON.ContactMaterial(defaultMaterial, defaultMaterial, {
    friction,
    restitution,
  });
  world.addContactMaterial(contactMat);

  // Static floor
  const floorBody = new CANNON.Body({
    type: CANNON.Body.STATIC,
    shape: new CANNON.Plane(),
    material: defaultMaterial,
  });
  floorBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
  world.addBody(floorBody);
}

function addBox(
  size: [number, number, number],
  pos: [number, number, number],
  rot: [number, number, number] | undefined,
  mass: number,
  color: string
) {
  const half = [size[0] / 2, size[1] / 2, size[2] / 2];
  const shape = new CANNON.Box(new CANNON.Vec3(half[0], half[1], half[2]));
  const body = new CANNON.Body({ mass, shape, material: defaultMaterial });
  body.position.set(pos[0], pos[1], pos[2]);
  if (rot) body.quaternion.setFromEuler(rot[0], rot[1], rot[2]);
  world.addBody(body);

  const geo = new THREE.BoxGeometry(size[0], size[1], size[2]);
  const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.4, metalness: 0.2 });
  const mesh = new THREE.Mesh(geo, mat);
  scene.add(mesh);

  pairs.push({ mesh, body });
  updateBadge();
}

function addSphere(
  radius: number,
  pos: [number, number, number],
  vel: [number, number, number] | undefined,
  mass: number,
  color: string
) {
  const shape = new CANNON.Sphere(radius);
  const body = new CANNON.Body({ mass, shape, material: defaultMaterial });
  body.position.set(pos[0], pos[1], pos[2]);
  if (vel) body.velocity.set(vel[0], vel[1], vel[2]);
  world.addBody(body);

  const geo = new THREE.SphereGeometry(radius, 20, 20);
  const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.3, metalness: 0.3 });
  const mesh = new THREE.Mesh(geo, mat);
  scene.add(mesh);

  pairs.push({ mesh, body });
  updateBadge();
}

function updateBadge() {
  el("badge-bodies").textContent = `Bodies: ${pairs.length}`;
}

function shootCannonball(targetPoint?: THREE.Vector3) {
  const radius = 0.8;
  const mass = 15; // Heavy projectile
  const shape = new CANNON.Sphere(radius);
  const body = new CANNON.Body({ mass, shape, material: defaultMaterial });

  // Shoot from camera position
  body.position.set(camera.position.x, camera.position.y, camera.position.z);

  const dir = new THREE.Vector3();
  if (targetPoint) {
    dir.subVectors(targetPoint, camera.position).normalize();
  } else {
    camera.getWorldDirection(dir);
  }

  const speed = 40;
  body.velocity.set(dir.x * speed, dir.y * speed, dir.z * speed);
  world.addBody(body);

  const geo = new THREE.SphereGeometry(radius, 16, 16);
  const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color("#fbbf24"), emissive: new THREE.Color("#b45309"), roughness: 0.2, metalness: 0.8 });
  const mesh = new THREE.Mesh(geo, mat);
  scene.add(mesh);

  pairs.push({ mesh, body });
  updateBadge();
}

function setupControls(canvas: HTMLCanvasElement) {
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
    updateCamera();
  });

  canvas.addEventListener("mouseup", (e) => {
    const moved = Math.hypot(e.clientX - prevMouse.x, e.clientY - prevMouse.y);
    isDragging = false;

    // If it was a click (not a drag), shoot a cannonball at the clicked point!
    if (moved < 5) {
      const rect = canvas.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);

      // Intersect with ground or bodies
      const targetPoint = raycaster.ray.origin.clone().add(raycaster.ray.direction.clone().multiplyScalar(25));
      shootCannonball(targetPoint);
    }
  });

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    spherical.radius = Math.max(10, Math.min(60, spherical.radius + e.deltaY * 0.05));
    updateCamera();
  }, { passive: false });

  // Button toolbar
  el("btn-cannonball").addEventListener("click", () => shootCannonball());

  el("btn-spawn-box").addEventListener("click", () => {
    const rx = (Math.random() - 0.5) * 6;
    const rz = (Math.random() - 0.5) * 6;
    addBox([1.2, 1.2, 1.2], [rx, 10, rz], undefined, 2, "#38bdf8");
  });

  el("btn-spawn-sphere").addEventListener("click", () => {
    const rx = (Math.random() - 0.5) * 6;
    const rz = (Math.random() - 0.5) * 6;
    addSphere(0.7, [rx, 10, rz], undefined, 2, "#f43f5e");
  });

  el("btn-reset").addEventListener("click", () => {
    if (currentSpec) buildWorld(currentSpec);
  });

  // Gravity selector
  const gBtns = document.querySelectorAll<HTMLButtonElement>("#physics-widget [data-g]");
  gBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      gBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const gType = btn.getAttribute("data-g");
      let gVal = -9.82;
      if (gType === "moon") gVal = -1.62;
      else if (gType === "zero_g") gVal = 0.0;
      else if (gType === "jupiter") gVal = -24.79;

      world.gravity.set(0, gVal, 0);
      el("badge-gravity").textContent = `Gravity: ${gVal} m/s²`;
    });
  });
}

function buildWorld(spec: PhysicsWorldSpec) {
  currentSpec = spec;

  // Clear previous
  pairs.forEach((p) => {
    scene.remove(p.mesh);
    world.removeBody(p.body);
  });
  pairs.length = 0;

  initCannon(spec.gravity, spec.restitution, spec.friction);

  for (const o of spec.objects) {
    if (o.type === "sphere") {
      addSphere(o.radius || 0.8, o.position, o.velocity, o.mass, o.color);
    } else {
      addBox(o.size || [1, 1, 1], o.position, o.rotation, o.mass, o.color);
    }
  }

  el("physics-title").textContent = spec.title || "Physics Playground";
  el("physics-desc").textContent = spec.description || "";
  el("badge-gravity").textContent = `Gravity: ${spec.gravity} m/s²`;
}

function loop() {
  requestAnimationFrame(loop);

  if (world) {
    world.fixedStep();

    for (const p of pairs) {
      p.mesh.position.copy(p.body.position as any);
      p.mesh.quaternion.copy(p.body.quaternion as any);
    }
  }

  renderer.render(scene, camera);
}

(window as any).renderWorld = (w: PhysicsWorldSpec) => buildWorld(w);

window.addEventListener("message", (e) => {
  if (e.data?.physicsWorld) buildWorld(e.data.physicsWorld);
  if (e.data?.params?.structuredContent?.physicsWorld) buildWorld(e.data.params.structuredContent.physicsWorld);
});

async function init() {
  initThree();
  loop();

  app = new App({ name: "physics-playground-widget", version: "1.0.0" }, {});

  app.ontoolresult = (params: any) => {
    const sc = params?.structuredContent;
    if (sc?.physicsWorld) {
      buildWorld(sc.physicsWorld as PhysicsWorldSpec);
    }
  };

  try {
    await app.connect(new PostMessageTransport(window.parent, window.parent));
  } catch (e) {}
}

init();
