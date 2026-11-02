/** Deterministic environmental renderer shared by Music Studio preview/capture. */

export const MUSIC_STUDIO_FORMAT = "fabuloom.music-studio-project/0.1";
export const MUSIC_STUDIO_STYLE_PALETTES = Object.freeze({
  "topazioverse-living-worlds": { deep: "#060b1c", mid: "#182c63", accent: "#5478c8", gold: "#e6c77a", mist: "#b7c8ff", fog: "#91b4dd", spark: "#f5d98a", reflection: "#6e9cdd" },
  "obsidian-void": { deep: "#05040e", mid: "#211347", accent: "#5d4f9e", gold: "#d4b3ff", mist: "#a9a2d4", fog: "#74699d", spark: "#c6b7ff", reflection: "#695aaf" },
  "crystal-dawn": { deep: "#0b1727", mid: "#26547b", accent: "#4caeca", gold: "#f1d487", mist: "#d3f4ff", fog: "#9ad4d4", spark: "#ffe7a2", reflection: "#7bd3e8" },
  "gaia-contemplative": { deep: "#071713", mid: "#234a3e", accent: "#5a9b74", gold: "#e8d58a", mist: "#b9d8b1", fog: "#80b79a", spark: "#f3e39e", reflection: "#76b998" },
});

const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));

export function validateMusicStudioProject(project) {
  if (!project || project.format !== MUSIC_STUDIO_FORMAT) throw new TypeError("unsupported Music Studio project format");
  if (!project.source?.filename || !project.source?.analysis?.duration_ms) throw new TypeError("project source metadata is incomplete");
  if (!project.style?.palette) throw new TypeError("project style palette is missing");
  if (project.visual_policy?.narrator || project.visual_policy?.lip_sync || project.visual_policy?.characters?.length) throw new TypeError("Music Studio projects cannot contain narrators or characters");
  for (const mode of ["full", "short"]) {
    const timeline = project[mode];
    if (!timeline || !Number.isInteger(timeline.width) || !Number.isInteger(timeline.height) || !Number.isInteger(timeline.fps) || !Number.isInteger(timeline.duration_ms) || timeline.duration_ms <= 0) throw new TypeError(`${mode} timeline is invalid`);
    if (!Array.isArray(timeline.scenes) || !timeline.scenes.length) throw new TypeError(`${mode} timeline has no scenes`);
    let previous = -1;
    for (const scene of timeline.scenes) {
      if (!scene.id || scene.start_ms < 0 || scene.end_ms <= scene.start_ms || scene.start_ms < previous) throw new TypeError(`${mode} scene timing is invalid`);
      previous = scene.end_ms;
    }
  }
  const selection = project.short_selection;
  if (!selection || selection.end_ms - selection.start_ms < 15000 || selection.end_ms - selection.start_ms > 30000) throw new TypeError("short selection must be 15–30 seconds");
  return project;
}

export function shortRange(startMs, endMs, sourceDurationMs) {
  const start = Math.max(0, Math.round(Number(startMs) || 0));
  const end = Math.min(Math.max(start + 1, Number(sourceDurationMs) || start + 1), Math.round(Number(endMs) || 0));
  if (end <= start || end - start < 15000 || end - start > 30000) throw new RangeError("short selection must be between 15 and 30 seconds");
  return Object.freeze({ start_ms: start, end_ms: end, duration_ms: end - start });
}

export function waveformAt(project, timeMs) {
  const values = project?.analysis?.waveform?.values || [];
  const duration = Math.max(1, Number(project?.source?.analysis?.duration_ms) || 1);
  if (!values.length) return 0;
  return Number(values[Math.max(0, Math.min(values.length - 1, Math.floor((Math.max(0, timeMs) / duration) * values.length)))]) || 0;
}

export function sceneAt(timeline, timeMs) {
  return timeline.scenes.find((scene) => timeMs >= scene.start_ms && timeMs < scene.end_ms) || timeline.scenes[timeline.scenes.length - 1];
}

function rgba(hex, alpha) {
  const value = hex.replace("#", "");
  const number = Number.parseInt(value.length === 3 ? value.split("").map((item) => item + item).join("") : value, 16);
  return `rgba(${number >> 16 & 255},${number >> 8 & 255},${number & 255},${alpha})`;
}

function paletteColor(palette, key, fallback) {
  return palette?.[key] || fallback;
}

function drawParticles(context, width, height, timeMs, palette, energy, vertical, styleId) {
  const spark = paletteColor(palette, "spark", paletteColor(palette, "gold", "#e6c77a"));
  const mist = paletteColor(palette, "mist", "#b7c8ff");
  const count = vertical ? 52 : 64;
  context.save();
  context.globalCompositeOperation = "screen";
  for (let index = 0; index < count; index += 1) {
    const depth = 0.22 + (index % 7) / 9;
    const drift = timeMs * (0.004 + depth * 0.009);
    const x = (index * 197 + drift + Math.sin(timeMs / 1700 + index * 1.73) * width * 0.035) % width;
    const y = (index * 97 + Math.sin(timeMs / 890 + index * 1.73) * height * 0.055 + height * (0.08 + (index % 5) * 0.15)) % height;
    const radius = (0.65 + (index % 4) * 0.55) * depth + energy * (1.1 + depth);
    context.globalAlpha = 0.08 + depth * 0.16 + energy * 0.12;
    context.fillStyle = index % 6 === 0 || styleId === "crystal-dawn" ? spark : mist;
    context.beginPath(); context.arc(x, y, radius, 0, Math.PI * 2); context.fill();
    if (index % 11 === 0) {
      context.globalAlpha *= 0.55;
      context.strokeStyle = context.fillStyle;
      context.lineWidth = Math.max(0.5, radius * 0.35);
      context.beginPath(); context.moveTo(x - radius * 3, y); context.lineTo(x + radius * 3, y); context.moveTo(x, y - radius * 3); context.lineTo(x, y + radius * 3); context.stroke();
    }
  }
  context.restore();
}

function drawFog(context, width, height, timeMs, palette, energy, vertical, styleId) {
  const fog = paletteColor(palette, "fog", paletteColor(palette, "mist", "#b7c8ff"));
  const secondary = paletteColor(palette, "reflection", paletteColor(palette, "accent", "#7d63ff"));
  context.save();
  context.globalCompositeOperation = "screen";
  context.filter = "blur(18px)";
  for (let index = 0; index < 4; index += 1) {
    const phase = timeMs / (3400 + index * 420) + index * 1.4;
    const x = width * (0.16 + index * 0.25) + Math.sin(phase) * width * 0.07;
    const y = height * (vertical ? 0.58 + index * 0.075 : 0.55 + index * 0.08) + Math.cos(phase * 0.7) * height * 0.035;
    const radiusX = width * (vertical ? 0.26 : 0.22);
    const radiusY = height * (vertical ? 0.075 : 0.105);
    const gradient = context.createRadialGradient(x, y, 0, x, y, Math.max(radiusX, radiusY));
    gradient.addColorStop(0, rgba(index % 2 === 0 ? fog : secondary, 0.055 + energy * 0.045));
    gradient.addColorStop(1, rgba(fog, 0));
    context.fillStyle = gradient;
    context.beginPath(); context.ellipse(x, y, radiusX, radiusY, Math.sin(phase) * 0.12, 0, Math.PI * 2); context.fill();
  }
  context.restore();
  if (styleId === "gaia-contemplative") {
    context.save(); context.globalCompositeOperation = "screen"; context.globalAlpha = 0.08 + energy * 0.04; context.strokeStyle = fog; context.lineWidth = Math.max(1, height * 0.0012);
    context.beginPath(); context.moveTo(0, height * 0.72); context.bezierCurveTo(width * 0.28, height * 0.64, width * 0.64, height * 0.8, width, height * 0.68); context.stroke(); context.restore();
  }
}

function drawReflections(context, width, height, timeMs, palette, energy, vertical) {
  const reflection = paletteColor(palette, "reflection", paletteColor(palette, "accent", "#7d63ff"));
  const gold = paletteColor(palette, "gold", "#e6c77a");
  context.save(); context.globalCompositeOperation = "screen";
  const originY = height * (vertical ? 0.79 : 0.82);
  for (let index = 0; index < 8; index += 1) {
    const y = originY + index * height * (vertical ? 0.018 : 0.022) + Math.sin(timeMs / 900 + index) * height * 0.004;
    const widthScale = 0.08 + (index % 3) * 0.035 + energy * 0.025;
    const x = width * (0.16 + (index * 0.12) % 0.68);
    context.globalAlpha = 0.045 + energy * 0.055;
    context.strokeStyle = index % 3 === 0 ? gold : reflection;
    context.lineWidth = Math.max(1, height * 0.0013);
    context.beginPath(); context.moveTo(x - width * widthScale, y); context.quadraticCurveTo(x, y + Math.sin(timeMs / 680 + index) * height * 0.006, x + width * widthScale, y); context.stroke();
  }
  context.restore();
}

function drawOrganicFragments(context, width, height, timeMs, palette, energy, vertical, styleId) {
  const accent = paletteColor(palette, "accent", "#7d63ff");
  const spark = paletteColor(palette, "spark", paletteColor(palette, "gold", "#e6c77a"));
  context.save(); context.globalCompositeOperation = "screen";
  for (let index = 0; index < 12; index += 1) {
    const phase = timeMs / (1700 + index * 95) + index * 1.9;
    const x = width * (0.08 + ((index * 0.137) % 0.84)) + Math.sin(phase) * width * 0.018;
    const y = height * (vertical ? 0.15 + (index % 6) * 0.12 : 0.18 + (index % 5) * 0.13) + Math.cos(phase * 0.8) * height * 0.025;
    const length = Math.max(4, Math.min(width, height) * (0.008 + (index % 4) * 0.003) * (1 + energy * 0.35));
    context.globalAlpha = 0.07 + (index % 4) * 0.018 + energy * 0.045;
    context.strokeStyle = index % 4 === 0 || styleId === "crystal-dawn" ? spark : accent;
    context.lineWidth = Math.max(0.8, length * 0.12);
    context.beginPath();
    context.moveTo(x - length, y + length * 0.15);
    context.quadraticCurveTo(x - length * 0.15, y - length * 0.8, x + length, y);
    context.quadraticCurveTo(x + length * 0.1, y + length * 0.55, x - length, y + length * 0.15);
    context.stroke();
  }
  context.restore();
}

function displayTitle(project) {
  const title = project?.display_title || project?.source?.display_title || project?.source?.filename || project?.title || "Music Studio";
  return String(title).replace(/\.[^.]+$/, "").replace(/^Music Studio\s*[·:-]\s*/i, "").trim();
}

function drawTitle(context, title, width, height, vertical) {
  const maxWidth = width * (vertical ? 0.82 : 0.66);
  let fontSize = vertical ? 35 : 48;
  context.font = `650 ${fontSize}px Segoe UI`;
  while (fontSize > 22 && context.measureText(title).width > maxWidth) { fontSize -= 2; context.font = `650 ${fontSize}px Segoe UI`; }
  const words = title.split(/\s+/); const lines = []; let line = "";
  for (const word of words) { const next = line ? `${line} ${word}` : word; if (context.measureText(next).width > maxWidth && line) { lines.push(line); line = word; } else line = next; }
  if (line) lines.push(line); if (lines.length > 2) lines.splice(2, lines.length - 2);
  context.fillStyle = "rgba(255,248,220,.94)"; context.shadowColor = "rgba(0,0,0,.45)"; context.shadowBlur = 12;
  lines.forEach((item, index) => context.fillText(item, vertical ? width * 0.08 : width * 0.055, vertical ? height * 0.1 + index * fontSize * 1.08 : height * 0.12 + index * fontSize * 1.08));
  context.shadowBlur = 0;
}

function drawContainedScene(context, image, width, height, timeMs, scene, vertical) {
  if (!image?.naturalWidth) return;
  const progress = clamp((timeMs - scene.start_ms) / Math.max(1, scene.end_ms - scene.start_ms));
  const coverScale = Math.max(width / image.naturalWidth, height / image.naturalHeight);
  const zoom = Number(scene.camera?.zoom || 1) + progress * 0.035;
  const imageWidth = image.naturalWidth * coverScale * zoom;
  const imageHeight = image.naturalHeight * coverScale * zoom;
  const panX = Number(scene.camera?.pan_x || 0) + Math.sin(progress * Math.PI) * 0.014;
  const panY = Number(scene.camera?.pan_y || 0) + Math.cos(progress * Math.PI) * 0.01;
  context.save();
  context.globalAlpha = 0.43;
  context.filter = "blur(18px) saturate(1.15)";
  context.drawImage(image, (width - imageWidth) / 2 + panX * width, (height - imageHeight) / 2 + panY * height, imageWidth, imageHeight);
  context.restore();
  context.save();
  if (vertical) {
    const frameW = width * 0.88;
    const frameH = height * 0.66;
    const scale = Math.max(frameW / image.naturalWidth, frameH / image.naturalHeight) * 1.04;
    const w = image.naturalWidth * scale, h = image.naturalHeight * scale;
    context.shadowColor = "rgba(0,0,0,.48)"; context.shadowBlur = 42; context.shadowOffsetY = 18;
    context.drawImage(image, (width - w) / 2 + Math.sin(progress * Math.PI) * width * 0.02, height * 0.16 + (frameH - h) / 2, w, h);
    context.restore();
    context.save(); context.strokeStyle = "rgba(230,199,122,.45)"; context.lineWidth = 2; context.strokeRect(width * 0.06, height * 0.16, width * 0.88, height * 0.66); context.restore();
  } else {
    context.drawImage(image, (width - imageWidth) / 2 + panX * width, (height - imageHeight) / 2 + panY * height, imageWidth, imageHeight);
    context.restore();
  }
}

export function drawLivingWorldFrame(context, project, images = {}, timeMs = 0, mode = "full") {
  const timeline = project[mode] || project.full;
  const width = context.canvas.width, height = context.canvas.height, vertical = mode === "short";
  const palette = project.style?.palette || { deep: "#060b1c", mid: "#182c63", accent: "#7d63ff", gold: "#e6c77a", mist: "#b7c8ff" };
  const sourceTime = mode === "short" ? timeMs + Number(project.short_selection?.start_ms || 0) : timeMs;
  const energy = waveformAt(project, sourceTime);
  const scene = sceneAt(timeline, timeMs);
  const image = images[scene.asset_id];
  const gradient = context.createLinearGradient(0, 0, vertical ? 0 : width, height);
  gradient.addColorStop(0, palette.deep); gradient.addColorStop(0.54, palette.mid); gradient.addColorStop(1, "#03050d");
  context.fillStyle = gradient; context.fillRect(0, 0, width, height);
  drawContainedScene(context, image, width, height, timeMs, scene, vertical);
  const vignette = context.createRadialGradient(width * 0.5, height * 0.42, 0, width * 0.5, height * 0.42, Math.max(width, height) * 0.7);
  vignette.addColorStop(0, "rgba(0,0,0,0)"); vignette.addColorStop(1, "rgba(0,0,9,.62)");
  context.fillStyle = vignette; context.fillRect(0, 0, width, height);
  const styleId = project.style?.id || "topazioverse-living-worlds";
  drawFog(context, width, height, timeMs, palette, energy, vertical, styleId);
  drawReflections(context, width, height, timeMs, palette, energy, vertical);
  drawOrganicFragments(context, width, height, timeMs, palette, energy, vertical, styleId);
  drawParticles(context, width, height, timeMs, palette, energy, vertical, styleId);
  if (timeMs < 4200 || timeMs > Math.max(4200, timeline.duration_ms - 3200)) {
    context.save(); drawTitle(context, displayTitle(project), width, height, vertical); context.restore();
  }
}

