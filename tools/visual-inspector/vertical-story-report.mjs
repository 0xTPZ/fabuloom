#!/usr/bin/env node

/** Pixel-evidence report for a captured Mission 019 vertical story. */
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { decodePng } from "./png.mjs";
import { analyzeRenderedPixels } from "../../frontend/src/real-image-inspector.mjs";

function argument(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function required(name) {
  const value = argument(name);
  if (!value) throw new Error(`missing ${name}`);
  return value;
}

const profilePath = path.resolve(required("--profile"));
const framesPath = path.resolve(required("--frames"));
const outputPath = path.resolve(required("--output"));
const profile = JSON.parse(await readFile(profilePath, "utf8"));
const completePath = path.join(framesPath, "complete.json");
const complete = JSON.parse(await readFile(completePath, "utf8"));
const sceneSamples = profile.scenes.map((scene) => ({
  scene_id: scene.id,
  label: scene.label,
  time_ms: Math.round((scene.start_ms + scene.end_ms) / 2),
}));
const samples = sceneSamples.map((scene) => {
  const index = Math.max(0, Math.min(complete.frame_count - 1, Math.round(scene.time_ms / 1000 * complete.fps)));
  return { ...scene, frame_index: index, file: path.join(framesPath, `${String(index).padStart(6, "0")}.png`) };
});
const evidence = [];
for (const sample of samples) {
  const image = decodePng(await readFile(sample.file));
  evidence.push({ ...sample, analysis: analyzeRenderedPixels(image, { region: { left: 0, top: 0, right: image.width, bottom: image.height }, minComponentArea: 64 }) });
}
const report = {
  format: "fabuloom.visual-inspector-vertical-story/0.1",
  source: { profile: profilePath, frames: framesPath, complete: completePath },
  dimensions: complete.canvas,
  frame_count: complete.frame_count,
  timing_source: complete.timing_source,
  technical_overlay: complete.technical_overlay,
  narrator_bounds: profile.narrator,
  safe_area: profile.safe_area,
  samples: evidence,
  review: { required: true, state: "evidence-only", note: "Pixel analysis cannot certify artistic quality, lip-sync, scene intent, or anatomical correctness." },
};
await writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
const markdown = [
  "# Visual Inspector — Vertical Cinematic Story V1",
  "",
  `- Perfil: \`${profilePath}\``,
  `- Captura: \`${framesPath}\``,
  `- Canvas: \`${complete.canvas.width}×${complete.canvas.height}\`, ${complete.frame_count} frames a ${complete.fps} FPS.`,
  `- Fonte temporal: \`${complete.timing_source}\`.`,
  "- Overlay técnico no vídeo: não.",
  "- Estado: evidência de pixels; aprovação artística humana necessária.",
  "",
  "## Amostras",
  "",
  ...evidence.map((sample) => `- ${sample.label}: frame ${sample.frame_index}, ocupação de foreground ${(sample.analysis.foreground.occupancy * 100).toFixed(2)}%, confiança ${sample.analysis.foreground.confidence}, arquivo \`${sample.file}\`.`),
  "",
  "Limitações: o relatório não mede correção anatômica, intenção cinematográfica, legibilidade em todos os dispositivos nem sincronização fonética.",
  "",
].join("\n");
await writeFile(outputPath.replace(/\.json$/i, ".md"), markdown, "utf8");
console.log(`report=${outputPath}`);
