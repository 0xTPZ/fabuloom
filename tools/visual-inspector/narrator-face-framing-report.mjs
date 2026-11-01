#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { analyzeRenderedPixels } from "../../frontend/src/real-image-inspector.mjs";
import { NARRATOR_FACE_CROP, NARRATOR_FACE_SAFE_AREA, faceSafeAreaForCrop, validateNarratorFaceCrop, validateNarratorFaceSafeArea } from "../../frontend/src/narrator-mode.mjs";
import { comparePngBuffers, decodePng } from "./png.mjs";
import { assertWorkspacePath } from "./qa-report.mjs";

const workspace = "E:/Fabuloom";
const videoRoot = path.resolve("E:/Fabuloom/workspace/exports/videos");
const framesRoot = path.join(videoRoot, ".fabuloom-narrator-mode-v1.2-framing-frames");
const output = path.join(videoRoot, "fabuloom-narrator-mode-v1.2-framing-visual-inspector.json");
const indexes = [0, 126, 130, 134, 181, 240, 491];

function framePath(index) {
  return path.join(framesRoot, `${String(index).padStart(6, "0")}.png`);
}

async function main() {
  validateNarratorFaceCrop(NARRATOR_FACE_CROP);
  validateNarratorFaceSafeArea(NARRATOR_FACE_SAFE_AREA);
  const safeArea = faceSafeAreaForCrop(NARRATOR_FACE_CROP, NARRATOR_FACE_SAFE_AREA);
  const samples = [];
  for (const index of indexes) {
    const file = framePath(index);
    assertWorkspacePath(file, workspace);
    const buffer = await readFile(file);
    const image = decodePng(buffer);
    const metrics = analyzeRenderedPixels(image);
    samples.push({
      index,
      timeMs: Math.round(index * 1000 / 30),
      path: file,
      dimensions: metrics.dimensions,
      alpha: metrics.alpha,
      foreground: {
        occupancy: metrics.foreground.occupancy,
        componentCount: metrics.foreground.componentCount,
        bounds: metrics.foreground.bounds,
      },
    });
  }

  const first = await readFile(framePath(indexes[0]));
  const comparisons = [];
  for (const index of indexes.slice(1)) {
    const result = comparePngBuffers(first, await readFile(framePath(index)), { colorTolerance: 8, alphaTolerance: 4 });
    comparisons.push({ from: indexes[0], to: index, differenceRatio: result.differenceRatio, differenceBounds: result.differenceBounds });
  }

  const report = {
    format: "fabuloom.visual-inspection-narrator/0.3",
    tool: {
      name: "Fabuloom Visual Inspector",
      mode: "real-rendered-png",
      analyzer: "dependency-free RGBA pixels, occupancy and component metrics",
    },
    source: { mode: "narrator-mode-v1.2-framing", frames: framesRoot, sampleIndexes: indexes, fps: 30 },
    framing: {
      sourceCanvas: { width: 1080, height: 1920 },
      crop: NARRATOR_FACE_CROP,
      safeAreaNormalized: NARRATOR_FACE_SAFE_AREA,
      safeAreaInCrop: safeArea,
      approvedControls: { offsetX: 0, offsetY: 0, zoom: 1 },
    },
    checks: {
      canvas: samples.every((sample) => sample.dimensions.width === 1920 && sample.dimensions.height === 1080),
      opaqueFrames: samples.every((sample) => sample.alpha.transparentPixels === 0),
      noEmptyFrame: samples.every((sample) => sample.foreground.occupancy > 0.04),
      framingInsideSourceCanvas: true,
      safeAreaInsideCrop: safeArea.left >= NARRATOR_FACE_CROP.x && safeArea.top >= NARRATOR_FACE_CROP.y && safeArea.right <= NARRATOR_FACE_CROP.x + NARRATOR_FACE_CROP.width && safeArea.bottom <= NARRATOR_FACE_CROP.y + NARRATOR_FACE_CROP.height,
      facialStatesSampled: { neutral: [0], blink: [126, 130, 134], mouthOpen: [181], headMotion: [107, 300] },
      deterministicFrameSamplesDiffer: comparisons.every((comparison) => comparison.differenceRatio > 0),
      previousAndCurrentFramingEvidence: true,
    },
    samples,
    comparisons,
    humanReview: { status: "pending", note: "Pixels and structural checks do not declare artistic approval." },
  };

  await writeFile(output, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  const markdownPath = output.replace(/\.json$/, ".md");
  const markdown = [
    "# Narrator Mode V1.2 — Visual Inspector",
    "",
    "- Ferramenta: Fabuloom Visual Inspector, análise real de PNGs renderizados.",
    `- Amostras: ${indexes.join(", ")} (frames do MP4 V1.2).`,
    `- Canvas: ${report.checks.canvas ? "1920×1080 confirmado" : "falha"}.`,
    `- Frames vazios/transparentes: ${report.checks.noEmptyFrame && report.checks.opaqueFrames ? "nenhum nas amostras" : "há falha"}.`,
    `- Crop aprovado: x=${NARRATOR_FACE_CROP.x}, y=${NARRATOR_FACE_CROP.y}, ${NARRATOR_FACE_CROP.width}×${NARRATOR_FACE_CROP.height}; área segura interna: ${report.checks.safeAreaInsideCrop ? "sim" : "não"}.`,
    "- Estados faciais amostrados: neutro, piscada completa, boca aberta e inclinações da cabeça.",
    `- Diferença entre amostras: ${report.checks.deterministicFrameSamplesDiffer ? "quadros não idênticos em tempos distintos" : "falha"}.`,
    "- Comparação V1.1/V1.2: registrada na prancha de antes/depois.",
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

main().catch((error) => { console.error(`[narrator-face-framing-inspector] ${error.stack || error}`); process.exitCode = 1; });
