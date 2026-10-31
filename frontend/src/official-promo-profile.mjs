/** Versioned profile for the public Fabuloom Studio promotional trailer. */

export const OFFICIAL_PROMO_FORMAT = "fabuloom.official-promo/0.1";
const finite = (value) => typeof value === "number" && Number.isFinite(value);
const allowedKinds = new Set(["intro", "cinematic", "screen", "results", "community", "end"]);

function text(value, label) {
  if (typeof value !== "string" || !value.trim()) throw new TypeError(`${label} is required`);
}

function safePath(value, label) {
  text(value, label);
  if (value.startsWith("/") || value.includes("\\") || value.split("/").some((part) => !part || part === "." || part === "..") || /^[a-z]+:/i.test(value)) {
    throw new TypeError(`${label} must be a safe workspace-relative path`);
  }
}

export function wrapSubtitleText(value, maxCharacters = 46) {
  text(value, "subtitle text");
  if (!Number.isInteger(maxCharacters) || maxCharacters < 8) throw new RangeError("maxCharacters must be at least 8");
  const words = value.trim().split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (line && candidate.length > maxCharacters) { lines.push(line); line = word; } else line = candidate;
  }
  if (line) lines.push(line);
  return lines;
}

export function validateOfficialPromoProfile(profile) {
  if (!profile || typeof profile !== "object") throw new TypeError("official promo profile must be an object");
  if (profile.format !== OFFICIAL_PROMO_FORMAT) throw new TypeError(`unsupported official promo format: ${profile.format}`);
  for (const [key, label] of [["id", "profile id"], ["title", "profile title"], ["story_text", "profile story_text"]]) text(profile[key], label);
  const canvas = profile.canvas;
  if (!canvas || canvas.width !== 1080 || canvas.height !== 1920 || canvas.fps !== 30 || canvas.aspect_ratio !== "9:16") throw new TypeError("official promo must define 1080x1920 9:16 at 30 FPS");
  const audio = profile.audio;
  if (!audio || audio.provider !== "kokoro" || audio.voice_id !== "pm_santa" || audio.language !== "pt-BR") throw new TypeError("official promo audio must be Kokoro pm_santa pt-BR");
  for (const key of ["manifest", "voice_wav", "music_wav", "sfx_wav", "main_mix_wav", "tiktok_ready_wav"]) safePath(audio[key], `audio.${key}`);
  if (!Array.isArray(profile.scenes) || profile.scenes.length !== 6) throw new TypeError("official promo must contain six ordered scenes");
  let previousEnd = 0;
  for (const [index, scene] of profile.scenes.entries()) {
    if (!scene || typeof scene !== "object" || !allowedKinds.has(scene.kind)) throw new TypeError(`scene ${index} kind is invalid`);
    text(scene.id, `scene ${index} id`); text(scene.label, `scene ${index} label`); safePath(scene.image, `scene ${index} image`);
    if (!Number.isInteger(scene.start_ms) || !Number.isInteger(scene.end_ms) || scene.start_ms < previousEnd || scene.end_ms <= scene.start_ms) throw new TypeError(`scene ${index} has an invalid ordered interval`);
    if (!Array.isArray(scene.text_segment_ids) || scene.text_segment_ids.length < 1) throw new TypeError(`scene ${index} needs measured segment ids`);
    previousEnd = scene.end_ms;
  }
  const narrator = profile.narrator;
  if (!narrator || ![narrator.x, narrator.y, narrator.size].every(finite) || narrator.size <= 0 || narrator.x < 0 || narrator.y < 0 || narrator.x + narrator.size > canvas.width || narrator.y + narrator.size > canvas.height) throw new RangeError("narrator bounds are invalid");
  if (!Array.isArray(narrator.visible_in) || narrator.visible_in.length < 1) throw new TypeError("narrator visibility schedule is required");
  const safe = profile.safe_area;
  if (!safe || ![safe.left, safe.top, safe.right, safe.bottom].every(finite) || safe.left >= safe.right || safe.top >= safe.bottom) throw new TypeError("safe area is invalid");
  const subtitles = profile.subtitles;
  if (!subtitles || ![subtitles.x, subtitles.y, subtitles.width, subtitles.font_size].every(finite) || subtitles.width <= 0 || subtitles.font_size <= 0) throw new TypeError("subtitle placement is invalid");
  if (subtitles.x - subtitles.width / 2 < safe.left || subtitles.x + subtitles.width / 2 > safe.right || subtitles.y < safe.top || subtitles.y > safe.bottom) throw new RangeError("subtitles must remain in the safe area");
  const exportProfile = profile.export;
  if (!exportProfile || exportProfile.video_codec !== "h264" || exportProfile.audio_codec !== "aac" || exportProfile.width !== 1080 || exportProfile.height !== 1920) throw new TypeError("official promo export contract is invalid");
  text(profile.credits?.author, "credits.author"); text(profile.credits?.repository, "credits.repository");
  return profile;
}
