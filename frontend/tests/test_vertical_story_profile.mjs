import test from "node:test";
import assert from "node:assert/strict";
import { validateVerticalStoryProfile } from "../src/vertical-story-profile.mjs";

function validProfile() {
  return {
    format: "fabuloom.vertical-story/0.1",
    id: "vertical-story-v1",
    title: "O Segredo Sob Arenhast",
    story_text: "Texto original.",
    manifest: "vertical-story-v1/story.json",
    canvas: { width: 1080, height: 1920, fps: 30, aspect_ratio: "9:16" },
    audio: { provider: "kokoro", voice_id: "pm_santa", language: "pt-BR", voice_wav: "vertical-story-v1/voice.wav", mixed_wav: "vertical-story-v1/mixed.wav", timing_source: "measured_wav_segments", word_phoneme_viseme_timing: "unavailable" },
    narrator: { renderer: "NarratorAvatarRenderer", composition: "Santa V5 Narrator Mode V1.4", x: 52, y: 1300, size: 340 },
    safe_area: { left: 48, top: 100, right: 1032, bottom: 1710, platform_ui_bottom: 180 },
    subtitles: { x: 675, y: 1510, width: 690, font_size: 31, line_height: 43, max_lines: 3 },
    transitions: { crossfade_ms: 650 },
    scenes: [
      { id: "one", label: "Um", image: "vertical-story-v1/scenes/one.png", camera: "zoom_in", effect: "none", start_ms: 0, end_ms: 1000, text_segment_ids: ["s1"] },
      { id: "two", label: "Dois", image: "vertical-story-v1/scenes/two.png", camera: "pan_vertical", effect: "none", start_ms: 1000, end_ms: 2000, text_segment_ids: ["s2"] },
    ],
    soundtrack: { origin: "original deterministic local procedural composition", path: "vertical-story-v1/music.wav", gain: 0.18 },
    export: { video_codec: "h264", audio_codec: "aac", pixel_format: "yuv420p", width: 1080, height: 1920, fps: 30, audio_sample_rate: 24000, public_technical_overlay: false },
  };
}

test("accepts a valid versioned vertical story profile", () => {
  const profile = validProfile();
  assert.equal(validateVerticalStoryProfile(profile), profile);
});

test("rejects a canvas with the wrong aspect contract", () => {
  const profile = validProfile();
  profile.canvas.width = 1920;
  assert.throws(() => validateVerticalStoryProfile(profile), /1080x1920/);
});

test("rejects unsafe asset paths", () => {
  const profile = validProfile();
  profile.scenes[0].image = "../private.png";
  assert.throws(() => validateVerticalStoryProfile(profile), /safe workspace-relative/);
});

test("rejects narrator and subtitles outside the safe area", () => {
  const profile = validProfile();
  profile.narrator.x = 800;
  profile.subtitles.y = 1700;
  assert.throws(() => validateVerticalStoryProfile(profile), /narrator must stay inside/);
});
