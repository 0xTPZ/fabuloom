#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import {
  NARRATOR_FACE_ALPHA_BOUNDS,
  NARRATOR_FACE_ALPHA_TARGETS,
  NARRATOR_FACE_CROP,
  NARRATOR_FACE_REFERENCE,
  NARRATOR_FACE_SAFE_AREA,
  faceSafeAreaForCrop,
  validateNarratorFaceCrop,
  validateNarratorFaceSafeArea,
} from "../../frontend/src/narrator-mode.mjs";
import { analyzeRenderedPixels } from "../../frontend/src/real-image-inspector.mjs";
import { comparePngBuffers, decodePng } from "./png.mjs";
import { assertWorkspacePath } from "./qa-report.mjs";

const workspace = "E:/Fabuloom";
const videoRoot = path.resolve("E:/Fabuloom/workspace/exports/videos");
const framesRoot = path.join(videoRoot, ".fabuloom-narrator-mode-v1.3-face-alignment-frames");
const previousFramesRoot = path.join(videoRoot, ".fabuloom-narrator-mode-v1.2-framing-frames");
const output = path.join(videoRoot, "fabuloom-narrator-mode-v1.3-face-alignment-visual-inspector.json");
const indexes = [0, 107, 130, 181, 240, 300, 491];

function framePath(root, index) { return path.join(root, `${String(index).padStart(6, "0")}.png`); }

async function sampleFrame(root, index) {
  const file = framePath(root, index);
  assertWorkspacePath(file, workspace);
  const buffer = await readFile(file);
  const image = decodePng(buffer);
  const metrics = analyzeRenderedPixels(image);
  return {
    index,
    timeMs: Math.round(index * 1000 / 30),
    path: file,
    dimensions: metrics.dimensions,
    alpha: metrics.alpha,
    foreground: { occupancy: metrics.foreground.occupancy, componentCount: metrics.foreground.componentCount, bounds: metrics.foreground.bounds },
  };
}

async function main() {
  validateNarratorFaceCrop(NARRATOR_FACE_CROP);
  validateNarratorFaceSafeArea(NARRATOR_FACE_SAFE_AREA);
  const safeArea = faceSafeAreaForCrop(NARRATOR_FACE_CROP, NARRATOR_FACE_SAFE_AREA);
  const samples = await Promise.all(indexes.map((index) => sampleFrame(framesRoot, index)));
  const first = await readFile(framePath(framesRoot, indexes[0]));
  const comparisons = [];
  for (const index of indexes.slice(1)) {
    const result = comparePngBuffers(first, await readFile(framePath(framesRoot, index)), { colorTolerance: 8, alphaTolerance: 4 });
    comparisons.push({ from: indexes[0], to: index, differenceRatio: result.differenceRatio, differenceBounds: result.differenceBounds });
  }
  const beforeAfter = [];
  for (const index of [0, 130, 181, 240]) {
    const result = comparePngBuffers(await readFile(framePath(previousFramesRoot, index)), await readFile(framePath(framesRoot, index)), { colorTolerance: 8, alphaTolerance: 4 });
    beforeAfter.push({ index, differenceRatio: result.differenceRatio, differenceBounds: result.differenceBounds });
  }
  const report = {
    format: "fabuloom.visual-inspection-narrator-face-alignment/0.1",
    tool: { name: "Fabuloom Visual Inspector", mode: "real-rendered-png", analyzer: "dependency-free RGBA pixels, occupancy, components and deterministic PNG comparison" },
    source: { mode: "narrator-mode-v1.3-face-alignment", frames: framesRoot, previousFrames: previousFramesRoot, sampleIndexes: indexes, fps: 30 },
    coordinateSystem: {
      reference: NARRATOR_FACE_REFERENCE,
      alphaBoundsMeasuredInOfficialPngs: NARRATOR_FACE_ALPHA_BOUNDS,
      alphaTargetsInHeadLocalSpace: NARRATOR_FACE_ALPHA_TARGETS,
    },
    framing: { sourceCanvas: { width: 1080, height: 1920 }, crop: NARRATOR_FACE_CROP, safeAreaNormalized: NARRATOR_FACE_SAFE_AREA, safeAreaInCrop: safeArea },
    checks: {
      canvas: samples.every((sample) => sample.dimensions.width === 1920 && sample.dimensions.height === 1080),
      opaqueFrames: samples.every((sample) => sample.alpha.transparentPixels === 0),
      noEmptyFrame: samples.every((sample) => sample.foreground.occupancy > 0.04),
      safeAreaInsideCrop: safeArea.left >= NARRATOR_FACE_CROP.x && safeArea.top >= NARRATOR_FACE_CROP.y && safeArea.right <= NARRATOR_FACE_CROP.x + NARRATOR_FACE_CROP.width && safeArea.bottom <= NARRATOR_FACE_CROP.y + NARRATOR_FACE_CROP.height,
      facialStatesSampled: { neutral: [0], headMotion: [107, 300], blink: [130], mouthOpen: [181] },
      deterministicFrameSamplesDiffer: comparisons.every((comparison) => comparison.differenceRatio > 0),
      previousAndCurrentEvidenceDiffer: beforeAfter.every((comparison) => comparison.differenceRatio > 0),
      timingSource: "measured_wav_segment_ranges",
      wordPhonemeVisemeTiming: "unavailable",
    },
    samples,
    comparisons,
    beforeAfter,
    humanReview: { status: "pending", note: "Pixels and structural checks do not declare artistic approval." },
  };
  await writeFile(output, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  const markdownPath = output.replace(/\.json$/, ".md");
  const markdown = [
    "# Narrator Mode V1.3 — Visual Inspector · Face Alignment",
    "",
    "- Ferramenta: Fabuloom Visual Inspector, análise de PNGs reais do renderizador compartilhado.",
    `- Amostras: ${indexes.join(", ")} (frames V1.3, 30 fps).`,
    `- Canvas: ${report.checks.canvas ? "1920×1080 confirmado" : "falha"}.`,
    `- Frames vazios/transparentes: ${report.checks.noEmptyFrame && report.checks.opaqueFrames ? "nenhum nas amostras" : "há falha"}.`,
    `- Coordenadas: ${NARRATOR_FACE_REFERENCE.coordinateSystem}; cabeça ${NARRATOR_FACE_REFERENCE.width}×${NARRATOR_FACE_REFERENCE.height}.`,
    `- Alinhamento alfa: ${Object.keys(NARRATOR_FACE_ALPHA_TARGETS).length} camadas com caixas alvo; limites de origem medidos nos PNGs oficiais.`,
    `- Diferença entre tempos: ${report.checks.deterministicFrameSamplesDiffer ? "quadros não idênticos" : "falha"}.`,
    `- Evidência V1.2/V1.3: ${report.checks.previousAndCurrentEvidenceDiffer ? "comparação produz diferença em todas as amostras" : "falha"}.`,
    "- Estados: neutro, inclinação, piscada e boca aberta.",
    "- Dados fonéticos: indisponíveis; o movimento da boca continua baseado no envelope RMS.",
    "- Aprovação artística: revisão humana pendente.",
    "",
    "| Frame | Tempo (ms) | Ocupação foreground | Componentes | Dimensões |",
    "| ---: | ---: | ---: | ---: | --- |",
    ...samples.map((sample) => `| ${sample.index} | ${sample.timeMs} | ${sample.foreground.occupancy.toFixed(4)} | ${sample.foreground.componentCount} | ${sample.dimensions.width}×${sample.dimensions.height} |`),
    "",
  ].join("\n");
  await writeFile(markdownPath, `${markdown}\n`, "utf8");
  console.log(JSON.stringify({ json: output, markdown: markdownPath, checks: report.checks }, null, 2));
}

main().catch((error) => { console.error(`[narrator-face-alignment-inspector] ${error.stack || error}`); process.exitCode = 1; });
