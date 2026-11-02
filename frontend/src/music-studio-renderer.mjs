/** Deterministic environmental renderer shared by Music Studio preview/capture. */

export const MUSIC_STUDIO_FORMAT = "fabuloom.music-studio-project/0.1";

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

function drawParticles(context, width, height, timeMs, palette, energy) {
  context.save();
  for (let index = 0; index < 62; index += 1) {
    const x = (index * 197 + timeMs * (0.012 + index % 3 * 0.004)) % width;
    const y = (index * 97 + Math.sin(timeMs / 890 + index * 1.73) * height * 0.035 + height * 0.08) % height;
    const radius = 1 + (index % 4) * 0.55 + energy * 1.4;
    context.globalAlpha = 0.12 + (index % 5) * 0.025 + energy * 0.18;
    context.fillStyle = index % 5 === 0 ? palette.gold : palette.mist;
    context.beginPath(); context.arc(x, y, radius, 0, Math.PI * 2); context.fill();
  }
  context.restore();
}

function drawCrystals(context, width, height, timeMs, palette, energy, vertical) {
  const baseY = vertical ? height * 0.82 : height * 0.84;
  context.save();
  context.globalCompositeOperation = "screen";
  for (let index = 0; index < 9; index += 1) {
    const x = width * (0.08 + index * 0.115) + Math.sin(timeMs / 1800 + index) * width * 0.012;
    const h = height * (0.07 + (index % 4) * 0.022) * (1 + energy * 0.24);
    const glow = context.createRadialGradient(x, baseY - h * 0.4, 0, x, baseY - h * 0.4, h * 2.2);
    glow.addColorStop(0, rgba(palette.accent, 0.22 + energy * 0.24)); glow.addColorStop(1, rgba(palette.accent, 0));
    context.fillStyle = glow; context.fillRect(x - h * 2, baseY - h * 2, h * 4, h * 4);
    context.fillStyle = rgba(palette.accent, 0.22); context.strokeStyle = rgba(palette.mist, 0.22); context.lineWidth = 1;
    context.beginPath(); context.moveTo(x, baseY - h); context.lineTo(x + h * 0.33, baseY - h * 0.35); context.lineTo(x + h * 0.2, baseY); context.lineTo(x - h * 0.24, baseY); context.lineTo(x - h * 0.34, baseY - h * 0.48); context.closePath(); context.fill(); context.stroke();
  }
  context.restore();
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
  drawCrystals(context, width, height, timeMs, palette, energy, vertical);
  drawParticles(context, width, height, timeMs, palette, energy);
  context.save();
  const pulse = 0.07 + energy * 0.08;
  context.fillStyle = `rgba(125,99,255,${pulse})`; context.fillRect(vertical ? width * 0.08 : width * 0.05, vertical ? height * 0.85 : height * 0.8, vertical ? width * 0.84 : width * 0.9, vertical ? height * 0.08 : height * 0.12);
  context.fillStyle = palette.gold; context.font = `700 ${vertical ? 18 : 22}px Segoe UI`; context.letterSpacing = "2px"; context.fillText("TOPAZIOVERSE · LIVING WORLDS", vertical ? width * 0.08 : width * 0.055, vertical ? height * 0.9 : height * 0.87);
  if (timeMs < 3600) { context.fillStyle = "rgba(255,248,220,.94)"; context.font = `650 ${vertical ? 35 : 48}px Segoe UI`; context.fillText("O CHAMADO DO VAZIO", vertical ? width * 0.08 : width * 0.055, vertical ? height * 0.1 : height * 0.12); }
  context.restore();
}

