import assert from "node:assert/strict";
import { AudioTimelinePlayer, localAudioUrl } from "../src/audio.ts";

class FakeSource {
  connect() {}
  start() { this.started = true; }
  stop() {
    if (this.onended) this.onended();
  }
}

class FakeAnalyser {
  constructor() { this.fftSize = 32; }
  connect() {}
  getByteTimeDomainData(samples) { samples.fill(128); }
}

class FakeAudioContext {
  constructor() { this.currentTime = 0; this.destination = {}; }
  async resume() {}
  async close() {}
  async decodeAudioData() { return { duration: 0.2 }; }
  createBufferSource() { return new FakeSource(); }
  createAnalyser() { return new FakeAnalyser(); }
}

const manifest = {
  id: "player-manifest",
  timeline_id: "player-timeline",
  duration_ms: 400,
  segments: [
    { id: "one", audio_uri: "file:///E:/exports/one.wav", start_ms: 0, end_ms: 200, duration_ms: 200, metadata: { pause_after_ms: 100 } },
    { id: "two", audio_uri: "file:///E:/exports/two.wav", start_ms: 300, end_ms: 400, duration_ms: 100, metadata: { pause_after_ms: 0 } },
  ],
};

assert.equal(localAudioUrl("file:///E:/exports/one.wav"), "/exports/one.wav");
assert.equal(localAudioUrl("file:///E:/exports/../private.wav"), "/exports/private.wav");

const context = new FakeAudioContext();
const player = new AudioTimelinePlayer(manifest, {
  contextFactory: () => context,
  fetchImpl: async () => ({ ok: true, status: 200, arrayBuffer: async () => new ArrayBuffer(0) }),
});
await player.load();
assert.equal(player.state, "stopped");
await player.play();
assert.equal(player.state, "playing");
context.currentTime = 0.08;
assert.equal(player.positionMs, 80);
player.pause();
const pausedPosition = player.positionMs;
context.currentTime = 0.35;
assert.equal(player.positionMs, pausedPosition);
assert.equal(player.amplitude(), 0);
player.seek(300);
assert.equal(player.positionMs, 300);
await player.play();
context.currentTime = 0.36;
assert.equal(player.positionMs, 310);
player.stop();
assert.equal(player.state, "stopped");
assert.equal(player.positionMs, 0);

const emptyPlayer = new AudioTimelinePlayer({ id: "empty", timeline_id: "empty", duration_ms: 0, segments: [] }, {
  contextFactory: () => new FakeAudioContext(),
  fetchImpl: async () => { throw new Error("must not fetch empty timelines"); },
});
await emptyPlayer.load();
await emptyPlayer.play();
assert.equal(emptyPlayer.state, "ended");
assert.equal(emptyPlayer.amplitude(), 0);

const failingPlayer = new AudioTimelinePlayer(manifest, {
  contextFactory: () => new FakeAudioContext(),
  fetchImpl: async () => ({ ok: false, status: 503 }),
});
await assert.rejects(() => failingPlayer.load(), /could not load narration audio/);
assert.equal(failingPlayer.state, "error");

console.log("frontend audio player tests: ok");
