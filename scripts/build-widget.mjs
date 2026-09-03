import { build } from "esbuild";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

const outDir = path.join(root, "widget-src/generated");

async function bundleWidget(tsEntry, templateFile, outputFile) {
  const result = await build({
    entryPoints: [path.join(root, `widget-src/${tsEntry}`)],
    bundle: true,
    format: "iife",
    platform: "browser",
    target: "es2020",
    write: false,
    logLevel: "warning",
  });

  const bundledJs = result.outputFiles[0].text;
  const template = await readFile(path.join(root, `widget-src/${templateFile}`), "utf8");
  const html = template.replace("<!--WIDGET_SCRIPT-->", `<script>\n${bundledJs}\n</script>`);

  await mkdir(outDir, { recursive: true });
  await writeFile(path.join(outDir, outputFile), html, "utf8");
  console.log(`Widget bundled -> widget-src/generated/${outputFile}`);
}

async function main() {
  await bundleWidget(
    "mission-widget-src.ts",
    "template.html",
    "mission-widget.html"
  );
  await bundleWidget(
    "visualizer-widget-src.ts",
    "visualizer-template.html",
    "visualizer-widget.html"
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
