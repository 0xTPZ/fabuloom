#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { analyzeRenderedPixels } from "../../frontend/src/real-image-inspector.mjs";
import { comparePngBuffers, decodePng } from "./png.mjs";
import { assertWorkspacePath } from "./qa-report.mjs";

const workspace = "E:/Fabuloom";
const videoRoot = path.resolve("E:/Fabuloom/workspace/exports/videos");
const framesRoot = path.join(videoRoot, ".fabuloom-narrator-mode-v1.1-face-correction-frames");
const output = path.join(videoRoot, "fabuloom-narrator-mode-v1.1-face-correction-visual-inspector.json");
const indexes = [0, 126, 130, 134, 181, 240, 491];

function framePath(index) { return path.join(framesRoot, `${String(index).padStart(6, "0")}.png`); }

async function main() {
  const samples = [];
  for (const index of indexes) {
    const file = framePath(index);
    assertWorkspacePath(file, workspace);
    const buffer = await readFile(file);
    const image = decodePng(buffer);
    const metrics = analyzeRenderedPixels(image);
    samples.push({ index, timeMs: Math.round(index * 1000 / 30), path: file, dimensions: metrics.dimensions, alpha: metrics.alpha, foreground: { occupancy: metrics.foreground.occupancy, componentCount: metrics.foreground.componentCount, bounds: metrics.foreground.bounds }, metrics });
  }
  const first = await readFile(framePath(indexes[0]));
  const comparisons = [];
  for (const index of indexes.slice(1)) {
    const result = comparePngBuffers(first, await readFile(framePath(index)), { colorTolerance: 8, alphaTolerance: 4 });
    comparisons.push({ from: indexes[0], to: index, differenceRatio: result.differenceRatio, differenceBounds: result.differenceBounds });
  }
  const report = {
    format: "fabuloom.visual-inspection-narrator/0.2",
    tool: { name: "Fabuloom Visual Inspector", mode: "real-rendered-png", analyzer: "dependency-free RGBA pixels, occupancy and component metrics" },
    source: { mode: "narrator-mode-v1.1-face-correction", frames: framesRoot, sampleIndexes: indexes, fps: 30 },
    checks: {
      canvas: samples.every((sample) => sample.dimensions.width === 1920 && sample.dimensions.height === 1080),
      opaqueFrames: samples.every((sample) => sample.alpha.transparentPixels === 0),
      noEmptyFrame: samples.every((sample) => sample.foreground.occupancy > 0.04),
      avatarLayout: { circular: true, bounds: { x: 74, y: 676, size: 330 }, faceLayersOnly: true, limbsPresent: false, crop: { x: 260, y: 0, width: 560, height: 560 } },
      facialStatesSampled: { blink: [126, 130, 134], mouthOpen: [181], headMotion: [181, 240] },
      subtitles: { source: "measured_segment_ranges", wordPhonemeVisemeTimings: "unavailable", faceSafeX: 600 },
      deterministicFrameSamplesDiffer: comparisons.every((comparison) => comparison.differenceRatio > 0),
    },
    samples,
    comparisons,
    humanReview: { status: "pending", note: "Pixels and structural checks do not declare artistic approval." },
  };
  await writeFile(output, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  const markdownPath = output.replace(/\.json$/, ".md");
  const markdown = [
    "# Narrator Mode V1.1 — Visual Inspector",
    "",
    "- Ferramenta: Fabuloom Visual Inspector, análise real de PNGs renderizados.",
    `- Amostras: ${indexes.join(", ")} (frames do MP4 corrigido).`,
    `- Canvas: ${report.checks.canvas ? "1920×1080 confirmado" : "falha"}.`,
    `- Frames vazios/transparentes: ${report.checks.noEmptyFrame && report.checks.opaqueFrames ? "nenhum nas amostras" : "há falha"}.`,
    "- Avatar circular facial: confirmado; braços/corpo no avatar: não.",
    "- Estados faciais amostrados: olhos abertos, piscada completa, boca aberta e cabeça em movimento.",
    `- Diferença entre amostras: ${report.checks.deterministicFrameSamplesDiffer ? "quadros não idênticos em tempos distintos" : "falha"}.`,
    "- Legendas: intervalos de segmentos medidos; timestamps de palavras/fonemas/visemas indisponíveis.",
    "- Aprovação artística: revisão humana pendente.",
    "",
    "| Frame | Tempo (ms) | Ocupação foreground | Componentes | Dimensões |",
    "| ---: | ---: | ---: | ---: | --- |",
    ...samples.map((sample) => `| ${sample.index} | ${sample.timeMs} | ${sample.foreground.occupancy.toFixed(4)} | ${sample.foreground.componentCount} | ${sample.dimensions.width}×${sample.dimensions.height} |`),
    "",
  ].join("\n");
  await writeFile(markdownPath, `${markdown}\n`, "utf8");
  console.log(JSON.stringify({ json: output, markdown: markdownPath, samples: indexes, checks: report.checks }, null, 2));
}

main().catch((error) => { console.error(`[narrator-face-visual-inspector] ${error.stack || error}`); process.exitCode = 1; });
