import { build } from "esbuild";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

async function main() {
  const result = await build({
    entryPoints: [path.join(root, "widget-src/mission-widget-src.ts")],
    bundle: true,
    format: "iife",
    platform: "browser",
    target: "es2020",
    write: false,
    logLevel: "warning",
  });

  const bundledJs = result.outputFiles[0].text;
  const template = await readFile(path.join(root, "widget-src/template.html"), "utf8");
  const html = template.replace("<!--WIDGET_SCRIPT-->", `<script>\n${bundledJs}\n</script>`);

  const outDir = path.join(root, "widget-src/generated");
  await mkdir(outDir, { recursive: true });
  await writeFile(path.join(outDir, "mission-widget.html"), html, "utf8");
  console.log("Widget bundled -> widget-src/generated/mission-widget.html");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
