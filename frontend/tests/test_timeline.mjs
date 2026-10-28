import assert from "node:assert/strict";
import { PlaybackClock, findSegmentAt, validateManifest } from "../src/timeline.ts";

const manifest = {
  id: "test-manifest",
  timeline_id: "test-timeline",
  duration_ms: 1_000,
  segments: [
    { id: "one", start_ms: 0, end_ms: 400, duration_ms: 400 },
    { id: "two", start_ms: 500, end_ms: 1_000, duration_ms: 500 },
  ],
};

validateManifest(manifest);
assert.equal(findSegmentAt(manifest.segments, 100).id, "one");
assert.equal(findSegmentAt(manifest.segments, 450), null);
assert.equal(findSegmentAt(manifest.segments, 700).id, "two");

const clock = new PlaybackClock(1_000);
clock.play(0);
assert.equal(clock.update(250), 250);
clock.pause(250);
assert.equal(clock.update(800), 250);
clock.play(800);
assert.equal(clock.update(1_050), 500);
clock.seek(700, 1_050);
assert.equal(clock.update(1_150), 800);
clock.stop();
assert.equal(clock.position_ms, 0);
clock.play(0);
clock.update(1_000);
assert.equal(clock.state, "ended");

assert.throws(
  () => validateManifest({
    ...manifest,
    segments: [manifest.segments[0], { ...manifest.segments[1], start_ms: 300, duration_ms: 700 }],
  }),
  /overlaps/,
);

console.log("frontend timeline tests: ok");
