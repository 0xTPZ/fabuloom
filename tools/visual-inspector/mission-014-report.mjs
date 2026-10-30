import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { comparePngBuffers, decodePng, encodePng } from "./png.mjs";

const root = path.resolve("E:/Fabuloom/workspace/exports/visual-qa/mission-014");
const beforeDir = path.join(root, "audit-before", "production");
const afterDir = path.join(root, "audit-after", "production");
const productionDir = path.join(root, "audit-production-1080-final", "production");
const comparisonDir = path.join(root, "comparisons");
const closeupDir = path.join(root, "closeups");

function cropPng(input, bounds) {
  const image = decodePng(input);
  const left = Math.max(0, Math.min(image.width, Math.floor(bounds.left)));
  const top = Math.max(0, Math.min(image.height, Math.floor(bounds.top)));
  const right = Math.max(left + 1, Math.min(image.width, Math.ceil(bounds.right)));
  const bottom = Math.max(top + 1, Math.min(image.height, Math.ceil(bounds.bottom)));
  const width = right - left;
  const height = bottom - top;
  const rgba = Buffer.alloc(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    image.rgba.copy(rgba, y * width * 4, ((top + y) * image.width + left) * 4, ((top + y) * image.width + right) * 4);
  }
  return encodePng({ width, height, rgba });
}

async function compare(name, beforeName, afterName) {
  const beforePath = path.join(beforeDir, beforeName);
  const afterPath = path.join(afterDir, afterName);
  const result = comparePngBuffers(await readFile(beforePath), await readFile(afterPath), { colorTolerance: 12 });
  await writeFile(path.join(comparisonDir, `${name}-diff.png`), result.diffMaskPng);
  await writeFile(path.join(comparisonDir, `${name}-overlay.png`), result.overlayPng);
  return {
    name,
    beforePath,
    afterPath,
    diffPath: path.join(comparisonDir, `${name}-diff.png`),
    overlayPath: path.join(comparisonDir, `${name}-overlay.png`),
    differenceRatio: result.differenceRatio,
    differenceBounds: result.differenceBounds,
    compatible: result.compatible,
  };
}

async function closeup(name, sourceName, bounds) {
  const output = path.join(closeupDir, `${name}.png`);
  await writeFile(output, cropPng(await readFile(path.join(productionDir, sourceName)), bounds));
  return { name, sourceName, output, bounds };
}

await mkdir(comparisonDir, { recursive: true });
await mkdir(closeupDir, { recursive: true });

const comparisons = [
  await compare("wave-raised", "wave-raised.png", "wave-raised.png"),
  await compare("point-hold", "point-hold.png", "point-hold.png"),
];

const closeups = [
  await closeup("face-neutral", "face-close.png", { left: 0, top: 0, right: 680, bottom: 520 }),
  await closeup("face-blink", "blink.png", { left: 0, top: 0, right: 680, bottom: 520 }),
  await closeup("face-mouth", "mouth-open.png", { left: 0, top: 0, right: 680, bottom: 520 }),
  await closeup("wave-raised-hand", "wave-raised.png", { left: 500, top: 560, right: 820, bottom: 980 }),
  await closeup("point-right-hand", "point-hold.png", { left: 500, top: 650, right: 820, bottom: 1060 }),
  await closeup("point-left-hand", "point-left-hold.png", { left: 130, top: 650, right: 440, bottom: 1080 }),
  await closeup("feet-neutral", "feet-neutral.png", { left: 160, top: 1470, right: 650, bottom: 1770 }),
];

const report = {
  mission: "014",
  generatedAt: new Date().toISOString(),
  baseline: { directory: beforeDir, captureWidth: 680, captureHeight: 1920 },
  corrected: { directory: afterDir, captureWidth: 680, captureHeight: 1920 },
  production: { directory: productionDir, captureWidth: 1080, captureHeight: 1920, captureCount: 60 },
  corrections: [
    { id: "named-clip-anchor", status: "corrected", cause: "SantaV5SceneRenderer inherited the V3 walk-in scene position while a named presenter clip was active.", change: "V5 sceneAt override anchors named clips at the presenter position and keeps idle composition metadata." },
    { id: "left-point-composition", status: "corrected", cause: "The left POINT_AT arm reached outside the V5 character canvas when the presenter anchor remained at x=60.", change: "POINT_AT left target uses a presentation-only x=180 anchor; rig, assets and target IK remain unchanged." },
    { id: "capture-resolution", status: "corrected", cause: "The visual-inspector full-frame CLI used a 680px capture even though the production stage is 1080px wide.", change: "Full-frame CLI captures now use a 1080px browser window; facial close-ups remain intentionally compact." },
  ],
  remaining: [
    "The visual gate cannot approve artistic quality automatically; human review remains required.",
    "Santa V5 remains a rigid layered 2.5D character without mesh deformation or physics.",
    "Face close-up captures intentionally use a compact viewport and are not full-stage compositions.",
  ],
  comparisons,
  closeups,
};

const comparisonLabels = comparisons.map((item) => path.relative(root, item.overlayPath).replaceAll("\\", "/")).map((item) => `\`${item}\``).join(", ");
const closeupLabels = closeups.map((item) => path.relative(root, item.output).replaceAll("\\", "/")).map((item) => `\`${item}\``).join(", ");

await writeFile(path.join(root, "mission-014-visual-quality-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");

const markdown = [
  "# MISSÃO 014 — Santa V5 Visual Quality Recovery",
  "",
  "## Resultado",
  "",
  "A inspeção humana das capturas reais confirmou três defeitos de composição: deriva horizontal de clips nomeados, corte da mão/manga no POINT_AT esquerdo e captura full-frame abaixo da resolução de produção. Os três foram corrigidos e revalidados.",
  "",
  "## Correções rastreáveis",
  "",
  ...report.corrections.map((item) => `- **${item.id}** — ${item.change} Causa: ${item.cause}`),
  "",
  "## Evidência",
  "",
  `- Gate técnico: **passed**; 60 capturas em ${report.production.captureWidth}×${report.production.captureHeight}.`,
  `- Comparações antes/depois: ${comparisonLabels}.`,
  `- Prancha visual: \`${path.join(root, "santa-v5-visual-quality-board.png")}\`.`,
  `- Close-ups: ${closeupLabels}.`,
  "",
  "## Limitações restantes",
  "",
  ...report.remaining.map((item) => `- ${item}`),
  "",
  "A análise visual foi feita com inspeção multimodal local das PNGs geradas pelo pipeline; não foi declarado um resultado de visão por IA além das imagens efetivamente examinadas.",
  "",
].join("\n");
await writeFile(path.join(root, "mission-014-visual-quality-report.md"), markdown, "utf8");
console.log(JSON.stringify({ report: path.join(root, "mission-014-visual-quality-report.json"), markdown: path.join(root, "mission-014-visual-quality-report.md"), comparisons, closeups }, null, 2));
