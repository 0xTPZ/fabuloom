/** Real audio playback, timeline clock, and amplitude analysis boundary. */

import { PlaybackClock, findSegmentAt, validateManifest } from "./timeline.ts";

export function localAudioUrl(audioUri) {
  const filename = String(audioUri).split(/[\\/]/).pop();
  if (!filename || filename.includes("..")) {
    throw new Error("audio URI does not contain a safe local filename");
  }
  return `/exports/${encodeURIComponent(filename)}`;
}

export class AudioTimelinePlayer {
  constructor(manifest, options = {}) {
    validateManifest(manifest);
    this.manifest = manifest;
    this.contextFactory = options.contextFactory || (() => new AudioContext());
    this.fetchImpl = options.fetchImpl || globalThis.fetch.bind(globalThis);
    this.context = null;
    this.clock = new PlaybackClock(manifest.duration_ms);
    this.buffers = new Map();
    this.currentSource = null;
    this.currentSegment = null;
    this.analyser = null;
    this.timer = null;
    this.suppressEnded = false;
    this.smoothedAmplitude = 0;
    this.onStateChange = options.onStateChange || (() => {});
  }

  get state() {
    return this.clock.state;
  }

  get positionMs() {
    return this.clock.update(this.nowMs());
  }

  async load() {
    this.context = this.context || this.contextFactory();
    try {
      for (const segment of this.manifest.segments) {
        const response = await this.fetchImpl(localAudioUrl(segment.audio_uri));
        if (!response.ok) {
          throw new Error(`audio request failed with HTTP ${response.status}`);
        }
        const encoded = await response.arrayBuffer();
        const buffer = await this.context.decodeAudioData(encoded);
        this.buffers.set(segment.id, buffer);
      }
    } catch (error) {
      this.clock.state = "error";
      this.onStateChange(this.state, error);
      throw new Error(`could not load narration audio: ${error.message}`);
    }
    this.onStateChange("stopped");
    return this;
  }

  async play() {
    if (!this.context) {
      throw new Error("audio player must be loaded before play");
    }
    if (this.state === "error") {
      throw new Error("audio player is in an error state");
    }
    await this.context.resume();
    this.clock.play(this.nowMs());
    this.scheduleFromPosition();
    this.onStateChange(this.state);
  }

  pause() {
    if (!this.context || this.state !== "playing") return;
    this.clock.pause(this.nowMs());
    this.clearTimer();
    this.stopCurrentSource();
    this.onStateChange(this.state);
  }

  stop() {
    this.clearTimer();
    this.stopCurrentSource();
    this.clock.stop();
    this.smoothedAmplitude = 0;
    this.onStateChange(this.state);
  }

  seek(positionMs) {
    const wasPlaying = this.state === "playing";
    this.clearTimer();
    this.stopCurrentSource();
    this.clock.seek(positionMs, this.nowMs());
    if (wasPlaying && this.state !== "ended") {
      this.clock.play(this.nowMs());
      this.scheduleFromPosition();
    }
    this.onStateChange(this.state);
  }

  tick() {
    const position = this.positionMs;
    if (this.state === "ended") {
      this.clearTimer();
      this.stopCurrentSource();
    } else if (this.state === "playing" && !this.currentSource && this.timer === null) {
      this.scheduleFromPosition();
    }
    return position;
  }

  amplitude() {
    if (this.state !== "playing" || !this.analyser || !this.currentSource) {
      this.smoothedAmplitude *= 0.82;
      return this.smoothedAmplitude;
    }
    const samples = new Uint8Array(this.analyser.fftSize);
    this.analyser.getByteTimeDomainData(samples);
    let sum = 0;
    for (const sample of samples) {
      const normalized = (sample - 128) / 128;
      sum += normalized * normalized;
    }
    const rms = Math.sqrt(sum / samples.length);
    const level = Math.max(0, Math.min(1, (rms - 0.012) * 5.5));
    this.smoothedAmplitude = this.smoothedAmplitude * 0.72 + level * 0.28;
    return this.smoothedAmplitude;
  }

  activeSegment() {
    return findSegmentAt(this.manifest.segments, this.positionMs);
  }

  dispose() {
    this.stop();
    if (this.context && typeof this.context.close === "function") {
      this.context.close();
    }
  }

  nowMs() {
    return this.context ? this.context.currentTime * 1000 : 0;
  }

  scheduleFromPosition() {
    const position = this.positionMs;
    if (position >= this.manifest.duration_ms) {
      this.clock.end();
      this.onStateChange(this.state);
      return;
    }
    const segment = findSegmentAt(this.manifest.segments, position);
    if (!segment) {
      const next = this.manifest.segments.find((candidate) => candidate.start_ms > position);
      if (!next) {
        this.clock.end();
        this.onStateChange(this.state);
        return;
      }
      this.timer = setTimeout(() => {
        this.timer = null;
        if (this.state === "playing") this.scheduleFromPosition();
      }, Math.max(1, next.start_ms - position));
      return;
    }

    const buffer = this.buffers.get(segment.id);
    if (!buffer) {
      this.clock.state = "error";
      this.onStateChange(this.state, new Error(`missing decoded audio for ${segment.id}`));
      return;
    }
    const source = this.context.createBufferSource();
    const analyser = this.context.createAnalyser();
    analyser.fftSize = 1024;
    source.buffer = buffer;
    source.connect(analyser);
    analyser.connect(this.context.destination);
    const offsetSeconds = Math.max(0, (position - segment.start_ms) / 1000);
    const remainingMs = Math.max(1, segment.end_ms - position);
    this.currentSource = source;
    this.currentSegment = segment;
    this.analyser = analyser;
    source.onended = () => {
      if (this.suppressEnded || this.currentSource !== source) return;
      this.currentSource = null;
      this.currentSegment = null;
      this.analyser = null;
      this.clock.seek(segment.end_ms + (segment.metadata?.pause_after_ms || 0), this.nowMs());
      if (this.state === "playing") this.scheduleFromPosition();
    };
    source.start(0, offsetSeconds);
    this.timer = setTimeout(() => {
      this.timer = null;
      if (this.currentSource === source && this.state === "playing") {
        source.onended();
      }
    }, remainingMs);
  }

  stopCurrentSource() {
    if (!this.currentSource) return;
    const source = this.currentSource;
    this.currentSource = null;
    this.currentSegment = null;
    this.analyser = null;
    this.suppressEnded = true;
    try {
      source.stop();
    } catch (_error) {
      // Stopping an already ended Web Audio source is harmless.
    }
    this.suppressEnded = false;
  }

  clearTimer() {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}
