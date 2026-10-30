import { mkdir, readFile, writeFile } from "node:fs/promises";
import { decodePng } from "../visual-inspector/png.mjs";

const sourceRoot = new URL("../../frontend/assets/characters/topazio-narrators-v5/santa/", import.meta.url);
const experimentalRoot = new URL("../../frontend/assets/characters/topazio-narrators-v5/experimental-anatomy/", import.meta.url);
const outputRoot = new URL("../../../workspace/exports/visual-qa/mission-015/", import.meta.url);

async function metrics(url) {
  const image = decodePng(await readFile(url));
  let minX = image.width, minY = image.height, maxX = -1, maxY = -1, opaque = 0;
  for (let y = 0; y < image.height; y += 1) for (let x = 0; x < image.width; x += 1) {
    const alpha = image.rgba[(y * image.width + x) * 4 + 3];
    if (!alpha) continue;
    opaque += 1; minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  return { width: image.width, height: image.height, alpha_bounds: [minX, minY, maxX, maxY], alpha_coverage: Number((opaque / (image.width * image.height)).toFixed(4)) };
}

const sources = ["torso.png", "upper-arm-left.png", "forearm-left.png", "hand-left.png", "thigh-left.png", "shin-left.png", "foot-left.png"];
const experiments = ["upper-arm-left-anatomy.png", "forearm-left-anatomy.png", "cuff-left-anatomy.png"];
const sourceMetrics = Object.fromEntries(await Promise.all(sources.map(async (file) => [file, await metrics(new URL(file, sourceRoot))])));
const experimentalMetrics = Object.fromEntries(await Promise.all(experiments.map(async (file) => [file, await metrics(new URL(file, experimentalRoot))])));
const report = {
  mission: "015",
  generated_at: new Date().toISOString(),
  source_of_truth: "frontend/assets/characters/topazio-narrators-v5/santa",
  official_assets_modified: false,
  experimental_assets: "frontend/assets/characters/topazio-narrators-v5/experimental-anatomy",
  alpha_metrics: { source: sourceMetrics, experimental: experimentalMetrics },
  evidence: {
    anatomy_gallery: "workspace/exports/visual-qa/mission-015-anatomy-gallery-final.png",
    arm_comparison: "workspace/exports/visual-qa/mission-015-arm-comparison-final.png",
    boots_comparison: "workspace/exports/visual-qa/mission-015-boots-comparison.png",
    experimental_demo: "workspace/exports/videos/fabuloom-santa-v5-anatomy-experimental.mp4",
  },
  mesh_deformation: {
    godot: "not-available-on-path",
    inochi2d: "not-available-on-path",
    blender: "no-blender-executable-found",
    proof_of_concept: "not-executed",
    reason: "No local executable was available and no software was installed under this mission.",
  },
};
await mkdir(outputRoot, { recursive: true });
await writeFile(new URL("mission-015-anatomy-report.json", outputRoot), JSON.stringify(report, null, 2), "utf8");
const rows = Object.entries(sourceMetrics).map(([file, value]) => `| ${file} | ${value.width}×${value.height} | ${value.alpha_bounds.join(", ")} | ${value.alpha_coverage} |`).join("\n");
const experimentalRows = Object.entries(experimentalMetrics).map(([file, value]) => `| ${file} | ${value.width}×${value.height} | ${value.alpha_bounds.join(", ")} | ${value.alpha_coverage} |`).join("\n");
const markdown = [
  "# Mission 015 — Anatomy-first audit",
  "",
  "- Official Santa V5 assets modified: **no**.",
  "- Experimental source: frontend/assets/characters/topazio-narrators-v5/experimental-anatomy.",
  "- Renderer: existing LayeredCharacterRenderer; no second animation engine.",
  "- Mesh deformation: **not executed**. Godot, Inochi2D and Blender executables were unavailable locally; no installation was attempted.",
  "",
  "## Evidence",
  "",
  "- Anatomy gallery: workspace/exports/visual-qa/mission-015-anatomy-gallery.png.",
  "- Arm comparison: workspace/exports/visual-qa/mission-015-arm-comparison.png.",
  "- Boots comparison: workspace/exports/visual-qa/mission-015-boots-comparison.png.",
  "- Experimental motion demo: workspace/exports/videos/fabuloom-santa-v5-anatomy-experimental.mp4.",
  "",
  "## Alpha metrics — approved source",
  "",
  "| Asset | Frame | Alpha bounds (x0,y0,x1,y1) | Coverage |",
  "|---|---:|---:|---:|",
  rows,
  "",
  "## Alpha metrics — experimental bands",
  "",
  "| Asset | Frame | Alpha bounds (x0,y0,x1,y1) | Coverage |",
  "|---|---:|---:|---:|",
  experimentalRows,
  "",
  "## Interpretation",
  "",
  "The current defect is structural: the approved arm source contains overlapping painted volumes, so changing pivots alone cannot create a convincing elbow. The experimental pack masks the upper-arm and forearm bands, introduces an independent cuff node, enlarges the hand draw size, and tests a smaller boot scale. These are reversible derived assets, not replacements.",
  "",
  "The rigid and reconstructed-assets approaches are demonstrated with equivalent neutral and WAVE_HELLO poses. A weighted-mesh comparison remains pending until a permitted local tool is available. Artistic approval is intentionally left to human review.",
  "",
].join("\n");
await writeFile(new URL("mission-015-anatomy-report.md", outputRoot), markdown, "utf8");
console.log(JSON.stringify(report, null, 2));
