import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";

interface SandboxSpec {
  title: string;
  html: string;
  css: string;
  javascript: string;
}

let app: App;
let currentSpec: SandboxSpec = {
  title: "Web Component Preview",
  html: "<div style='padding: 24px; text-align: center;'><h2>Hello Web Sandbox!</h2><p>Previewing components in real time.</p></div>",
  css: "body { font-family: sans-serif; color: #1e293b; background: #f8fafc; }",
  javascript: "",
};

const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

function renderPreview() {
  const frame = el<HTMLIFrameElement>("preview-frame");
  const html = (el<HTMLTextAreaElement>("code-html")).value;
  const css = (el<HTMLTextAreaElement>("code-css")).value;
  const js = (el<HTMLTextAreaElement>("code-js")).value;

  const doc = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    ${css}
  </style>
</head>
<body>
  ${html}
  <script>
    try {
      ${js}
    } catch (e) {
      console.error('Preview error:', e);
    }
  <\/script>
</body>
</html>`;

  frame.srcdoc = doc;
}

function setupUI(spec: SandboxSpec) {
  currentSpec = spec;
  el("sandbox-title").textContent = spec.title || "Web Component Preview";

  el<HTMLTextAreaElement>("code-html").value = spec.html || "";
  el<HTMLTextAreaElement>("code-css").value = spec.css || "";
  el<HTMLTextAreaElement>("code-js").value = spec.javascript || "";

  renderPreview();

  // Tab switching
  const tabs = document.querySelectorAll<HTMLButtonElement>("#sandbox-widget .tab-btn");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const targetTab = tab.getAttribute("data-tab");
      document.querySelectorAll("#sandbox-widget .content-view").forEach((view) => {
        view.classList.remove("active");
      });

      const activeView = el(`view-${targetTab}`);
      if (activeView) activeView.classList.add("active");

      if (targetTab === "preview") {
        renderPreview();
      }
    });
  });

  // Responsive device view buttons
  const frame = el<HTMLIFrameElement>("preview-frame");
  el("view-desktop").addEventListener("click", () => {
    frame.style.width = "100%";
    frame.style.boxShadow = "none";
  });
  el("view-mobile").addEventListener("click", () => {
    frame.style.width = "375px";
    frame.style.boxShadow = "0 10px 25px -5px rgba(0,0,0,0.15)";
  });

  // Reload button
  el("reload-btn").addEventListener("click", () => {
    renderPreview();
  });

  // Live reload on code edit
  ["code-html", "code-css", "code-js"].forEach((id) => {
    el(id).addEventListener("input", () => {
      renderPreview();
    });
  });
}

async function init() {
  app = new App({ name: "web-sandbox-widget", version: "1.0.0" }, {});

  app.ontoolresult = (params: any) => {
    const sc = params?.structuredContent;
    if (sc?.sandbox) {
      setupUI(sc.sandbox as SandboxSpec);
    }
  };

  await app.connect(new PostMessageTransport(window.parent, window.parent));
}

init();
