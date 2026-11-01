import { FABULOOM_KEYFRAME_FORMAT, validateAnimationClip } from "./animation-keyframes.mjs";
import { angleDelta, solveTwoBoneIK } from "./two-bone-ik.mjs";
import { resolvePresentationTarget, targetDirection } from "./presentation-targets.mjs";

export const POINT_AT_DEFAULT_DURATION_MS = 8000;
export const POINT_AT_DEFAULT_HOLD_MS = 4100;
export const POINT_AT_CHANNELS = Object.freeze([
  "point_at_weight",
  "point_head_weight",
  "point_torso_weight",
  "point_hand_rotation",
]);

const finite = (value) => typeof value === "number" && Number.isFinite(value);
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function positiveInteger(value, label) {
  if (!Number.isInteger(value) || value <= 0) throw new RangeError(`${label} must be a positive integer`);
  return value;
}

/**
 * Create a target-independent POINT_AT clip. Target coordinates are supplied
 * at runtime by the presenter adapter, so one clip can point to any region.
 */
export function createPointAtClip({
  durationMs = POINT_AT_DEFAULT_DURATION_MS,
  holdMs,
  attentionMs = 600,
  anticipationMs = 500,
  elevationMs = 1400,
  returnMs = 1400,
  id = "POINT_AT",
} = {}) {
  positiveInteger(durationMs, "POINT_AT duration");
  for (const [label, value] of Object.entries({ attentionMs, anticipationMs, elevationMs, returnMs })) positiveInteger(value, `POINT_AT ${label}`);
  const derivedHoldMs = durationMs - attentionMs - anticipationMs - elevationMs - returnMs;
  const effectiveHoldMs = holdMs === undefined ? derivedHoldMs : holdMs;
  positiveInteger(effectiveHoldMs, "POINT_AT hold");
  const fixed = attentionMs + anticipationMs + elevationMs + effectiveHoldMs + returnMs;
  if (fixed > durationMs) throw new RangeError("POINT_AT phases exceed duration");
  const sustainMs = durationMs - returnMs;
  const raiseEnd = attentionMs + anticipationMs + elevationMs;
  const anticipationEnd = attentionMs + anticipationMs;
  const returnStart = sustainMs;
  const clip = {
    format: FABULOOM_KEYFRAME_FORMAT,
    id,
    durationMs,
    easing: "ease-in-out",
    keyframes: [
      { timeMs: 0, easing: "ease-in-out", channels: { point_at_weight: 0, point_head_weight: 0, point_torso_weight: 0, point_hand_rotation: 0 } },
      { timeMs: attentionMs, easing: "ease-out", channels: { point_at_weight: 0, point_head_weight: 0.28, point_torso_weight: 0.08, point_hand_rotation: 0 } },
      { timeMs: anticipationEnd, easing: "ease-in-out", channels: { point_at_weight: 0.10, point_head_weight: 0.58, point_torso_weight: 0.36, point_hand_rotation: 0 } },
      { timeMs: raiseEnd, easing: "ease-out", channels: { point_at_weight: 1, point_head_weight: 1, point_torso_weight: 1, point_hand_rotation: 0 } },
      { timeMs: returnStart, easing: "linear", channels: { point_at_weight: 1, point_head_weight: 1, point_torso_weight: 1, point_hand_rotation: 0 } },
      { timeMs: Math.max(returnStart + 1, durationMs - Math.round(returnMs * 0.45)), easing: "ease-in", channels: { point_at_weight: 0.42, point_head_weight: 0.42, point_torso_weight: 0.34, point_hand_rotation: 0 } },
      { timeMs: durationMs, easing: "ease-in-out", channels: { point_at_weight: 0, point_head_weight: 0, point_torso_weight: 0, point_hand_rotation: 0 } },
    ],
  };
  // The hold is implicit between raiseEnd and returnStart. Keep this check
  // close to construction so future phase changes cannot silently remove it.
  if (returnStart - raiseEnd !== effectiveHoldMs) throw new RangeError("POINT_AT hold phase is inconsistent");
  return validateAnimationClip(clip, { allowedChannels: new Set(POINT_AT_CHANNELS) });
}

function normalizedPoint(point, width, height) { return { x: point.x / width, y: point.y / height }; }

/**
 * Convert a scene target into a comfortable wrist target and a pointer
 * orientation. The hand stops short of the object; the indicator direction
 * carries the last part of the gesture. Unreachable targets are clamped by
 * the existing IK solver, while the returned direction still aims at them.
 */
export function planPointAtTarget(target, {
  calibration,
  width = calibration?.frameWidth || 1080,
  height = calibration?.frameHeight || 1920,
  objects,
  wristClearancePx = 86,
  pointerLocalAngle = Math.PI / 2,
  elbowPreference,
  arm = "right",
} = {}) {
  if (!calibration) throw new TypeError("POINT_AT calibration is required");
  if (![width, height, wristClearancePx, pointerLocalAngle].every(finite) || width <= 0 || height <= 0 || wristClearancePx < 0) throw new TypeError("Invalid POINT_AT planning dimensions");
  const resolved = resolvePresentationTarget(target, { width, height, objects });
  if (arm !== "left" && arm !== "right") throw new RangeError("POINT_AT arm must be left or right");
  const shoulder = calibration.shoulder;
  const targetAngle = targetDirection(shoulder, resolved.point);
  const distance = Math.hypot(resolved.point.x - shoulder.x, resolved.point.y - shoulder.y);
  const direction = distance < 1e-6
    ? { x: Math.cos(targetAngle), y: Math.sin(targetAngle) }
    : { x: (resolved.point.x - shoulder.x) / distance, y: (resolved.point.y - shoulder.y) / distance };
  const minimumWristDistance = Math.abs(calibration.upperLength - calibration.forearmLength) + 6;
  const maximumWristDistance = calibration.upperLength + calibration.forearmLength - 6;
  const unconstrainedWristDistance = distance - wristClearancePx;
  const desiredDistance = clamp(unconstrainedWristDistance, minimumWristDistance, maximumWristDistance);
  const wristTarget = {
    x: shoulder.x + direction.x * desiredDistance,
    y: shoulder.y + direction.y * desiredDistance,
  };
  const sidePreference = elbowPreference || (resolved.point.x < shoulder.x ? { x: -1, y: 0.55 } : { x: 1, y: 0.55 });
  const analytic = solveTwoBoneIK({
    shoulder,
    target: wristTarget,
    upperLength: calibration.upperLength,
    forearmLength: calibration.forearmLength,
    elbowPreference: sidePreference,
    limits: { shoulder: [-2.35, 2.15], elbow: [-3.12, 3.12] },
  });
  const horizontal = clamp((resolved.point.x - width / 2) / (width * 0.42), -1, 1);
  const vertical = clamp((resolved.point.y - height * 0.33) / (height * 0.44), -1, 1);
  const headRotation = clamp(horizontal * 0.082 - vertical * 0.012, -0.10, 0.10);
  const torsoRotation = clamp(horizontal * 0.032, -0.06, 0.06);
  const pointerDirection = targetAngle;
  const normalizedWrist = normalizedPoint(wristTarget, width, height);
  const targetOutOfReach = unconstrainedWristDistance < minimumWristDistance || unconstrainedWristDistance > maximumWristDistance;
  return Object.freeze({
    target: resolved,
    arm,
    shoulder,
    wristTarget: Object.freeze(wristTarget),
    normalizedWrist: Object.freeze(normalizedWrist),
    wristClearancePx,
    pointerDirection,
    pointerLocalAngle,
    elbowPreference: Object.freeze({ x: sidePreference.x, y: sidePreference.y }),
    headRotation,
    torsoRotation,
    requestedDistance: distance,
    wristDistance: desiredDistance,
    reachable: analytic.reachable && !targetOutOfReach,
    clamped: analytic.clamped || targetOutOfReach,
    targetOutOfReach,
    analytic,
  });
}

export function pointerRotationForIK(ik, plan, calibration) {
  const forearmWorld = calibration.baseShoulderAngle + ik.shoulderRotation + calibration.baseElbowAngle + ik.elbowRotation;
  return angleDelta(forearmWorld + plan.pointerLocalAngle, plan.pointerDirection);
}
