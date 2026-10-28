/** Pure timeline validation and clock primitives used by the visual stage. */

export function validateManifest(manifest) {
  if (!manifest || typeof manifest !== "object") {
    throw new Error("manifest must be an object");
  }
  if (!Array.isArray(manifest.segments)) {
    throw new Error("manifest.segments must be an array");
  }
  if (!Number.isInteger(manifest.duration_ms) || manifest.duration_ms < 0) {
    throw new Error("manifest.duration_ms must be a non-negative integer");
  }
  const ids = new Set();
  let previousEnd = 0;
  for (const segment of manifest.segments) {
    if (!segment || typeof segment !== "object") {
      throw new Error("manifest contains an invalid segment");
    }
    if (!segment.id || ids.has(segment.id)) {
      throw new Error(`duplicate or empty segment id: ${segment.id}`);
    }
    ids.add(segment.id);
    for (const key of ["start_ms", "end_ms", "duration_ms"]) {
      if (!Number.isInteger(segment[key]) || segment[key] < 0) {
        throw new Error(`segment ${segment.id} has invalid ${key}`);
      }
    }
    if (segment.end_ms - segment.start_ms !== segment.duration_ms) {
      throw new Error(`segment ${segment.id} duration does not match its range`);
    }
    if (segment.start_ms < previousEnd) {
      throw new Error(`segment ${segment.id} overlaps the previous segment`);
    }
    if (segment.end_ms > manifest.duration_ms) {
      throw new Error(`segment ${segment.id} exceeds manifest duration`);
    }
    previousEnd = segment.end_ms;
  }
  return manifest;
}

export function findSegmentAt(segments, positionMs) {
  return segments.find((segment) => segment.start_ms <= positionMs && positionMs < segment.end_ms) || null;
}

export function clampPosition(positionMs, durationMs) {
  return Math.max(0, Math.min(durationMs, Math.round(positionMs)));
}

export class PlaybackClock {
  constructor(durationMs) {
    this.duration_ms = durationMs;
    this.state = "stopped";
    this.position_ms = 0;
    this.anchor_ms = 0;
  }

  play(nowMs) {
    if (this.position_ms >= this.duration_ms) {
      this.position_ms = 0;
    }
    this.anchor_ms = nowMs - this.position_ms;
    this.state = "playing";
  }

  pause(nowMs) {
    this.update(nowMs);
    if (this.state === "playing") {
      this.state = "paused";
    }
  }

  stop() {
    this.state = "stopped";
    this.position_ms = 0;
  }

  seek(positionMs, nowMs) {
    this.position_ms = clampPosition(positionMs, this.duration_ms);
    if (this.state === "playing") {
      this.anchor_ms = nowMs - this.position_ms;
    }
    if (this.position_ms >= this.duration_ms && this.duration_ms > 0) {
      this.state = "ended";
    }
  }

  end() {
    this.position_ms = this.duration_ms;
    this.state = "ended";
  }

  update(nowMs) {
    if (this.state === "playing") {
      this.position_ms = clampPosition(nowMs - this.anchor_ms, this.duration_ms);
      if (this.position_ms >= this.duration_ms && this.duration_ms > 0) {
        this.state = "ended";
      }
    }
    return this.position_ms;
  }
}
