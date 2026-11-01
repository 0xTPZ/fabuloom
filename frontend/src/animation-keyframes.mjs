/**
 * Deterministic, provider- and character-independent numeric animation clips.
 * Values are additive channel deltas; the character rig decides how channels
 * map to layers. A clip can therefore be sampled after a seek or out of order.
 */

export const FABULOOM_KEYFRAME_FORMAT = "fabuloom.animation-keyframes/0.1";

export const KEYFRAME_EASINGS = Object.freeze([
  "linear",
  "smoothstep",
  "ease-in",
  "ease-out",
  "ease-in-out",
]);

const easingSet = new Set(KEYFRAME_EASINGS);
const identifierPattern = /^[A-Za-z][A-Za-z0-9_-]{1,63}$/;

const isFiniteNumber = (value) => typeof value === "number" && Number.isFinite(value) && !Number.isNaN(value);
const isPlainObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

function valid(condition, message) {
  if (!condition) throw new TypeError(message);
}

function validateChannels(channels, allowedChannels) {
  valid(isPlainObject(channels), "Animation keyframe channels must be an object");
  for (const [channel, value] of Object.entries(channels)) {
    valid(identifierPattern.test(channel), `Invalid animation channel: ${channel}`);
    valid(isFiniteNumber(value), `Animation channel ${channel} must be a finite number`);
    if (allowedChannels) valid(allowedChannels.has(channel), `Unsupported animation channel: ${channel}`);
  }
}

/** Validate and return a clip without mutating it. */
export function validateAnimationClip(clip, { allowedChannels } = {}) {
  valid(isPlainObject(clip), "Animation clip must be an object");
  valid(clip.format === FABULOOM_KEYFRAME_FORMAT, "Unsupported animation keyframe format");
  valid(typeof clip.id === "string" && identifierPattern.test(clip.id), "Invalid animation clip id");
  valid(Number.isInteger(clip.durationMs) && clip.durationMs > 0, "Animation clip duration must be a positive integer");
  valid(easingSet.has(clip.easing || "smoothstep"), "Unsupported animation clip easing");
  valid(Array.isArray(clip.keyframes) && clip.keyframes.length >= 1, "Animation clip needs keyframes");

  let previousTime = -1;
  for (const [index, keyframe] of clip.keyframes.entries()) {
    valid(isPlainObject(keyframe), `Animation keyframe ${index} must be an object`);
    valid(Number.isInteger(keyframe.timeMs) && keyframe.timeMs >= 0 && keyframe.timeMs <= clip.durationMs, `Invalid time for animation keyframe ${index}`);
    valid(keyframe.timeMs > previousTime, "Animation keyframe times must be strictly increasing");
    valid(index !== 0 || keyframe.timeMs === 0, "Animation clips must start at time 0");
    valid(!keyframe.easing || easingSet.has(keyframe.easing), `Unsupported easing for animation keyframe ${index}`);
    validateChannels(keyframe.channels, allowedChannels);
    previousTime = keyframe.timeMs;
  }
  valid(clip.keyframes.at(-1).timeMs <= clip.durationMs, "Animation keyframe exceeds clip duration");
  return clip;
}

function curve(name, value) {
  const t = Math.max(0, Math.min(1, value));
  if (name === "linear") return t;
  if (name === "ease-in") return t * t;
  if (name === "ease-out") return 1 - ((1 - t) ** 2);
  if (name === "ease-in-out") return t < 0.5 ? 2 * t * t : 1 - ((-2 * t + 2) ** 2) / 2;
  return t * t * (3 - 2 * t);
}

function channelNames(a, b) {
  return new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
}

/** Sample an immutable numeric clip at any absolute clip time. */
export function sampleAnimationClip(clip, timeMs) {
  validateAnimationClip(clip);
  const safeTime = Math.max(0, Math.min(clip.durationMs, Number.isFinite(timeMs) ? timeMs : 0));
  const keyframes = clip.keyframes;
  if (safeTime <= keyframes[0].timeMs) return { ...keyframes[0].channels };
  const last = keyframes.at(-1);
  if (safeTime >= last.timeMs) return { ...last.channels };

  let index = 0;
  while (index < keyframes.length - 1 && safeTime > keyframes[index + 1].timeMs) index += 1;
  const from = keyframes[index];
  const to = keyframes[index + 1];
  const rawProgress = (safeTime - from.timeMs) / (to.timeMs - from.timeMs);
  const progress = curve(to.easing || clip.easing || "smoothstep", rawProgress);
  const result = {};
  for (const name of channelNames(from.channels, to.channels)) {
    const start = from.channels[name] ?? to.channels[name] ?? 0;
    const end = to.channels[name] ?? start;
    result[name] = start + (end - start) * progress;
  }
  return result;
}

/** Add compatible numeric channel sets without introducing frame state. */
export function blendAnimationChannels(base, overlay, weight = 1) {
  validateChannels(base || {});
  validateChannels(overlay || {});
  valid(isFiniteNumber(weight), "Animation blend weight must be finite");
  const result = { ...(base || {}) };
  for (const [channel, value] of Object.entries(overlay || {})) result[channel] = (result[channel] || 0) + value * weight;
  return result;
}

/** Compose several additive layers in a deterministic order. */
export function composeAnimationChannels(...layers) {
  return layers.reduce((result, layer) => blendAnimationChannels(result, layer), {});
}
