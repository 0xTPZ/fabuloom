import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";

import { decodePng } from "./png.mjs";

export const HISTORICAL_DATASET_FORMAT = "fabuloom.visual-inspector-historical-dataset/0.1";

/**
 * The analyzer receives only the image path and broad composition ROI. Review
 * labels are intentionally kept in a separate post-hoc file.
 */
export const HISTORICAL_IMAGE_SPECS = Object.freeze([
  { id: "reference-v5-1s", set: "reference", version: "V5", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v5-1s.png", source: "workspace/exports/videos/fabuloom-santa-v5.mp4", timeSec: 1, conditions: "1080x1920 H.264 frame extracted with FFmpeg; production V5" },
  { id: "reference-v5-wave-2s", set: "reference", version: "V5", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v5-wave-2s.png", source: "workspace/exports/videos/fabuloom-santa-v5-wave-hello.mp4", timeSec: 2, conditions: "1080x1920 H.264 frame extracted with FFmpeg; WAVE_HELLO" },
  { id: "reference-v5-point-4s", set: "reference", version: "V5", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v5-point-4s.png", source: "workspace/exports/videos/fabuloom-santa-v5-point-at.mp4", timeSec: 4, conditions: "1080x1920 H.264 frame extracted with FFmpeg; POINT_AT" },
  { id: "reference-v5-head-clean", set: "reference", version: "V5", image: "workspace/exports/visual-inspector/mission-013.2-real/reference-head-clean/neutral.png", source: "studio/frontend/assets/characters/topazio-narrators-v5/santa/head-clean.png", timeSec: 0, conditions: "same-run Canvas capture using the approved clean head asset" },
  { id: "evaluation-v5-head-original", set: "evaluation", version: "V5", image: "workspace/exports/visual-inspector/mission-013.2-real/historical-head-original/neutral.png", source: "studio/frontend/assets/characters/topazio-narrators-v5/santa/head.png", timeSec: 0, conditions: "same-run Canvas replay of the preserved historical head asset; production pack untouched" },
  { id: "evaluation-v3-1s", set: "evaluation", version: "V3", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v3-1s.png", source: "workspace/exports/videos/fabuloom-santa-v3.mp4", timeSec: 1, conditions: "1080x1920 H.264 frame extracted with FFmpeg" },
  { id: "evaluation-v3-10s", set: "evaluation", version: "V3", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v3-10s.png", source: "workspace/exports/videos/fabuloom-santa-v3.mp4", timeSec: 10, conditions: "1080x1920 H.264 frame extracted with FFmpeg" },
  { id: "evaluation-v3-18s", set: "evaluation", version: "V3", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v3-18s.png", source: "workspace/exports/videos/fabuloom-santa-v3.mp4", timeSec: 18, conditions: "1080x1920 H.264 frame extracted with FFmpeg" },
  { id: "evaluation-v4-1s", set: "evaluation", version: "V4", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v4-1s.png", source: "workspace/exports/videos/fabuloom-santa-v4.mp4", timeSec: 1, conditions: "1080x1920 H.264 frame extracted with FFmpeg" },
  { id: "evaluation-v4-10s", set: "evaluation", version: "V4", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v4-10s.png", source: "workspace/exports/videos/fabuloom-santa-v4.mp4", timeSec: 10, conditions: "1080x1920 H.264 frame extracted with FFmpeg" },
  { id: "evaluation-v4-18s", set: "evaluation", version: "V4", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v4-18s.png", source: "workspace/exports/videos/fabuloom-santa-v4.mp4", timeSec: 18, conditions: "1080x1920 H.264 frame extracted with FFmpeg" },
  { id: "evaluation-v5-10s", set: "evaluation", version: "V5", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v5-10s.png", source: "workspace/exports/videos/fabuloom-santa-v5.mp4", timeSec: 10, conditions: "1080x1920 H.264 frame extracted with FFmpeg; production V5" },
  { id: "evaluation-v5-18s", set: "evaluation", version: "V5", image: "workspace/exports/visual-inspector/mission-013.2-real/santa-v5-18s.png", source: "workspace/exports/videos/fabuloom-santa-v5.mp4", timeSec: 18, conditions: "1080x1920 H.264 frame extracted with FFmpeg; production V5" },
]);

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function resolvedWorkspacePath(workspaceRoot, relative) {
  return path.resolve(workspaceRoot, relative);
}

export async function buildHistoricalDatasetManifest({ workspaceRoot, specs = HISTORICAL_IMAGE_SPECS } = {}) {
  if (!workspaceRoot) throw new TypeError("workspaceRoot is required");
  const entries = [];
  for (const spec of specs) {
    const imagePath = resolvedWorkspacePath(workspaceRoot, spec.image);
    const imageBuffer = await readFile(imagePath);
    const image = decodePng(imageBuffer);
    const sourcePath = resolvedWorkspacePath(workspaceRoot, spec.source);
    const sourceStat = await stat(sourcePath);
    const sourceBuffer = await readFile(sourcePath);
    entries.push({
      id: spec.id,
      set: spec.set,
      version: spec.version,
      image: spec.image.replaceAll("\\", "/"),
      source: spec.source.replaceAll("\\", "/"),
      sourceKind: spec.source.endsWith(".mp4") ? "historical-video" : "historical-preserved-asset-replay",
      sourceTimeSec: spec.timeSec,
      conditions: spec.conditions,
      sha256: sha256(imageBuffer),
      sourceSha256: sha256(sourceBuffer),
      imageBytes: imageBuffer.length,
      sourceBytes: sourceStat.size,
      modifiedAt: (await stat(imagePath)).mtime.toISOString(),
      dimensions: { width: image.width, height: image.height },
      analysisRegion: { left: 80, top: 620, right: 760, bottom: 1820 },
    });
  }
  return {
    format: HISTORICAL_DATASET_FORMAT,
    generatedAt: new Date().toISOString(),
    evaluationPolicy: "The analyzer receives image pixels and broad composition regions only. Review labels are post-hoc and stored separately.",
    referenceIds: entries.filter((entry) => entry.set === "reference").map((entry) => entry.id),
    evaluationIds: entries.filter((entry) => entry.set === "evaluation").map((entry) => entry.id),
    entries,
  };
}
