import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { MUSIC_STUDIO_STYLE_PALETTES, shortRange, validateMusicStudioProject } from "../src/music-studio-renderer.mjs";

test("Music Studio short range is measured and bounded", () => {
  assert.deepEqual(shortRange(1000, 25000, 180000), { start_ms: 1000, end_ms: 25000, duration_ms: 24000 });
  assert.throws(() => shortRange(0, 10000, 180000), /15/);
  assert.throws(() => shortRange(0, 40000, 180000), /30/);
});

test("Music Studio project rejects narrator or character payloads", () => {
  const timeline = { width: 1920, height: 1080, fps: 30, duration_ms: 30000, scenes: [{ id: "scene", start_ms: 0, end_ms: 30000 }] };
  const project = { format: "fabuloom.music-studio-project/0.1", source: { filename: "track.mp3", analysis: { duration_ms: 30000 } }, style: { palette: {} }, visual_policy: { narrator: null, lip_sync: false, characters: [] }, full: timeline, short: { ...timeline, width: 1080, height: 1920, duration_ms: 24000 }, short_selection: { start_ms: 0, end_ms: 24000 } };
  assert.equal(validateMusicStudioProject(project), project);
  assert.throws(() => validateMusicStudioProject({ ...project, visual_policy: { narrator: "Santa V5", lip_sync: false, characters: [] } }), /narrators/);
});

test("V1.1 uses dynamic titles and organic ambient effects", () => {
  const renderer = fs.readFileSync(new URL("../src/music-studio-renderer.mjs", import.meta.url), "utf8");
  assert.equal(MUSIC_STUDIO_STYLE_PALETTES["gaia-contemplative"].fog, "#80b79a");
  assert.match(renderer, /displayTitle\(project\)/);
  assert.doesNotMatch(renderer, /O CHAMADO DO VAZIO/);
  assert.doesNotMatch(renderer, /drawCrystals/);
  assert.doesNotMatch(renderer, /TOPAZIOVERSE · LIVING WORLDS/);
});
