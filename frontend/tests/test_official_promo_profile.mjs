import test from "node:test";
import assert from "node:assert/strict";
import { validateOfficialPromoProfile, wrapSubtitleText } from "../src/official-promo-profile.mjs";

function profile() {
  const scenes = ["intro", "cinematic", "screen", "results", "community", "end"].map((kind, index) => ({
    id: `scene-${index + 1}`, label: kind, kind, image: `official-promo/scene-${index + 1}.png`, start_ms: index * 1000, end_ms: (index + 1) * 1000, text_segment_ids: [`segment-${index + 1}`],
  }));
  return {
    format: "fabuloom.official-promo/0.1", id: "official-promo-v1", title: "FABULOOM STUDIO — SUA HISTÓRIA GANHA VIDA", story_text: "Texto original.",
    canvas: { width: 1080, height: 1920, fps: 30, aspect_ratio: "9:16" },
    audio: { provider: "kokoro", voice_id: "pm_santa", language: "pt-BR", manifest: "official-promo/story.json", voice_wav: "official-promo/voice.wav", music_wav: "official-promo/music.wav", sfx_wav: "official-promo/sfx.wav", main_mix_wav: "official-promo/main.wav", tiktok_ready_wav: "official-promo/tiktok.wav" },
    scenes, narrator: { x: 48, y: 1400, size: 320, visible_in: ["scene-2", "scene-3", "scene-4"] },
    safe_area: { left: 48, top: 110, right: 1032, bottom: 1710 }, subtitles: { x: 540, y: 1510, width: 930, font_size: 30, line_height: 38 },
    export: { video_codec: "h264", audio_codec: "aac", width: 1080, height: 1920 }, credits: { author: "0xTPZ", repository: "https://github.com/0xTPZ/fabuloom" },
  };
}

test("accepts the six-scene official promo contract", () => {
  const value = profile();
  assert.equal(validateOfficialPromoProfile(value), value);
});

test("rejects wrong voice, unsafe paths and incomplete scene schedules", () => {
  const wrongVoice = profile(); wrongVoice.audio.voice_id = "pf_dora";
  assert.throws(() => validateOfficialPromoProfile(wrongVoice), /pm_santa/);
  const unsafe = profile(); unsafe.audio.manifest = "../private.json";
  assert.throws(() => validateOfficialPromoProfile(unsafe), /safe workspace-relative/);
  const incomplete = profile(); incomplete.scenes.pop();
  assert.throws(() => validateOfficialPromoProfile(incomplete), /six ordered scenes/);
});

test("subtitle wrapping preserves every word instead of clipping overflow", () => {
  const source = "Esta é uma frase longa que precisa continuar inteira na legenda do trailer.";
  const lines = wrapSubtitleText(source, 18);
  assert.equal(lines.join(" "), source);
  assert.ok(lines.length > 3);
});
