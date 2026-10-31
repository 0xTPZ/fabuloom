/** Versioned, provider-independent profile for vertical cinematic stories. */

export const VERTICAL_STORY_FORMAT = "fabuloom.vertical-story/0.1";

const finite = (value) => typeof value === "number" && Number.isFinite(value);

function assertText(value, label) {
  if (typeof value !== "string" || !value.trim()) throw new TypeError(`${label} is required`);
}

function assertSafeRelativePath(value, label) {
  assertText(value, label);
  if (value.startsWith("/") || value.includes("\\") || value.split("/").some((part) => !part || part === "." || part === "..") || /^[a-z]+:/i.test(value)) {
    throw new TypeError(`${label} must be a safe workspace-relative path`);
  }
}

function assertRange(value, label, min, max) {
  if (!finite(value) || value < min || value > max) throw new TypeError(`${label} must be in [${min},${max}]`);
}

export function validateVerticalStoryProfile(profile) {
  if (!profile || typeof profile !== "object") throw new TypeError("vertical story profile must be an object");
  if (profile.format !== VERTICAL_STORY_FORMAT) throw new TypeError(`unsupported vertical story format: ${profile.format}`);
  assertText(profile.id, "profile id");
  assertText(profile.title, "profile title");
  assertText(profile.story_text, "profile story_text");
  const canvas = profile.canvas;
  if (!canvas || canvas.width !== 1080 || canvas.height !== 1920 || canvas.fps !== 30 || canvas.aspect_ratio !== "9:16") {
    throw new TypeError("vertical profile must define 1080x1920 9:16 at 30 FPS");
  }
  assertSafeRelativePath(profile.manifest, "profile manifest");
  if (!Array.isArray(profile.scenes) || profile.scenes.length < 1) throw new TypeError("vertical profile must contain scenes");
  let previousEnd = 0;
  for (const [index, scene] of profile.scenes.entries()) {
    if (!scene || typeof scene !== "object") throw new TypeError(`scene ${index} must be an object`);
    assertText(scene.id, `scene ${index} id`);
    assertSafeRelativePath(scene.image, `scene ${index} image`);
    if (!Number.isInteger(scene.start_ms) || !Number.isInteger(scene.end_ms) || scene.start_ms < previousEnd || scene.end_ms <= scene.start_ms) throw new TypeError(`scene ${index} has an invalid ordered interval`);
    if (!Array.isArray(scene.text_segment_ids) || scene.text_segment_ids.length < 1) throw new TypeError(`scene ${index} must reference measured segments`);
    assertText(scene.camera, `scene ${index} camera`);
    previousEnd = scene.end_ms;
  }
  const narrator = profile.narrator;
  if (!narrator || !Number.isFinite(narrator.x) || !Number.isFinite(narrator.y) || !Number.isFinite(narrator.size) || narrator.size <= 0) throw new TypeError("narrator placement is invalid");
  if (narrator.x < 0 || narrator.y < 0 || narrator.x + narrator.size > canvas.width || narrator.y + narrator.size > canvas.height) throw new RangeError("narrator must stay inside the vertical canvas");
  const safe = profile.safe_area;
  if (!safe || ![safe.left, safe.top, safe.right, safe.bottom].every((value) => finite(value))) throw new TypeError("safe_area is required");
  assertRange(safe.left, "safe_area.left", 0, canvas.width);
  assertRange(safe.right, "safe_area.right", 0, canvas.width);
  assertRange(safe.top, "safe_area.top", 0, canvas.height);
  assertRange(safe.bottom, "safe_area.bottom", 0, canvas.height);
  if (safe.left >= safe.right || safe.top >= safe.bottom) throw new TypeError("safe_area must have positive dimensions");
  const subtitles = profile.subtitles;
  if (!subtitles || ![subtitles.x, subtitles.y, subtitles.width, subtitles.font_size].every(finite) || subtitles.width <= 0 || subtitles.font_size <= 0) throw new TypeError("subtitle profile is invalid");
  if (subtitles.x - subtitles.width / 2 < safe.left || subtitles.x + subtitles.width / 2 > safe.right || subtitles.y < safe.top || subtitles.y > safe.bottom) throw new RangeError("subtitles must remain inside the safe area");
  if (!profile.audio || !profile.audio.voice_id || profile.audio.language !== "pt-BR") throw new TypeError("audio voice and language are required");
  if (!profile.export || profile.export.video_codec !== "h264" || profile.export.audio_codec !== "aac") throw new TypeError("export codecs must be explicit");
  return profile;
}
