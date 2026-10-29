/**
 * Deterministic 2D two-bone inverse kinematics.
 *
 * Coordinates use the Canvas convention: +X points right, +Y points down and
 * angles are clockwise from +X, as returned by Math.atan2(y, x). The solver
 * never mutates its inputs and returns a reachable/clamped target, joint
 * angles, joint positions and the residual error to the requested target.
 */

const EPSILON = 1e-9;
const TAU = Math.PI * 2;

const finite = (value) => typeof value === "number" && Number.isFinite(value);
const point = (value, label) => {
  if (!value || !finite(value.x) || !finite(value.y)) throw new TypeError(`${label} must contain finite x and y`);
  return { x: value.x, y: value.y };
};

const distance = (a, b) => Math.hypot(b.x - a.x, b.y - a.y);
const normalizeAngle = (value) => {
  let angle = value % TAU;
  if (angle > Math.PI) angle -= TAU;
  if (angle <= -Math.PI) angle += TAU;
  return angle;
};
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function validateLimit(limit, label) {
  if (limit === undefined) return undefined;
  if (!Array.isArray(limit) || limit.length !== 2 || !finite(limit[0]) || !finite(limit[1]) || limit[0] > limit[1]) throw new TypeError(`${label} limit must be [min, max]`);
  return [limit[0], limit[1]];
}

function preferenceVector(preference) {
  const value = preference || { x: 1, y: 0 };
  const preferred = point(value, "elbowPreference");
  const length = Math.hypot(preferred.x, preferred.y);
  if (length < EPSILON) throw new RangeError("elbowPreference cannot be zero");
  return { x: preferred.x / length, y: preferred.y / length };
}

function candidatePose(shoulder, target, upperLength, forearmLength, shoulderAngle, elbowAngle) {
  const elbow = { x: shoulder.x + Math.cos(shoulderAngle) * upperLength, y: shoulder.y + Math.sin(shoulderAngle) * upperLength };
  const wrist = { x: elbow.x + Math.cos(shoulderAngle + elbowAngle) * forearmLength, y: elbow.y + Math.sin(shoulderAngle + elbowAngle) * forearmLength };
  return { shoulderAngle, elbowAngle, elbow, wrist, error: distance(wrist, target) };
}

function within(value, limit) { return !limit || (value >= limit[0] - EPSILON && value <= limit[1] + EPSILON); }

/**
 * Solve a two-segment chain. `limits.shoulder` and `limits.elbow` are angle
 * intervals in the coordinate convention documented above. Elbow preference
 * is a direction vector from the shoulder; the candidate whose elbow is most
 * aligned with that vector is selected, subject to limits.
 */
export function solveTwoBoneIK({ shoulder, target, upperLength, forearmLength, elbowPreference = { x: 1, y: 0 }, limits = {} }) {
  const origin = point(shoulder, "shoulder");
  const requestedTarget = point(target, "target");
  if (!finite(upperLength) || upperLength <= 0) throw new RangeError("upperLength must be positive and finite");
  if (!finite(forearmLength) || forearmLength <= 0) throw new RangeError("forearmLength must be positive and finite");
  const shoulderLimit = validateLimit(limits.shoulder, "shoulder");
  const elbowLimit = validateLimit(limits.elbow, "elbow");
  const preferred = preferenceVector(elbowPreference);
  const requestedDistance = distance(origin, requestedTarget);
  const minimumDistance = Math.abs(upperLength - forearmLength);
  const maximumDistance = upperLength + forearmLength;
  const reachable = requestedDistance >= minimumDistance - EPSILON && requestedDistance <= maximumDistance + EPSILON;
  const clampedDistance = clamp(requestedDistance, minimumDistance, maximumDistance);
  const direction = requestedDistance < EPSILON
    ? Math.atan2(preferred.y, preferred.x)
    : Math.atan2(requestedTarget.y - origin.y, requestedTarget.x - origin.x);
  const clampedTarget = {
    x: origin.x + Math.cos(direction) * clampedDistance,
    y: origin.y + Math.sin(direction) * clampedDistance,
  };
  const shoulderOffset = Math.acos(clamp((upperLength ** 2 + clampedDistance ** 2 - forearmLength ** 2) / (2 * upperLength * clampedDistance), -1, 1));
  const cosine = clamp((upperLength ** 2 + forearmLength ** 2 - clampedDistance ** 2) / (2 * upperLength * forearmLength), -1, 1);
  const bend = Math.acos(cosine);
  const candidates = [
    candidatePose(origin, clampedTarget, upperLength, forearmLength, direction - shoulderOffset, Math.PI - bend),
    candidatePose(origin, clampedTarget, upperLength, forearmLength, direction + shoulderOffset, -(Math.PI - bend)),
  ].map((candidate) => ({
    ...candidate,
    valid: within(candidate.shoulderAngle, shoulderLimit) && within(candidate.elbowAngle, elbowLimit),
    preferenceScore: ((candidate.elbow.x - origin.x) / upperLength) * preferred.x + ((candidate.elbow.y - origin.y) / upperLength) * preferred.y,
  }));
  const validCandidates = candidates.filter((candidate) => candidate.valid);
  const selected = [...(validCandidates.length ? validCandidates : candidates)].sort((a, b) => b.preferenceScore - a.preferenceScore)[0];
  const shoulderAngle = shoulderLimit ? clamp(selected.shoulderAngle, shoulderLimit[0], shoulderLimit[1]) : selected.shoulderAngle;
  const elbowAngle = elbowLimit ? clamp(selected.elbowAngle, elbowLimit[0], elbowLimit[1]) : selected.elbowAngle;
  const result = candidatePose(origin, clampedTarget, upperLength, forearmLength, shoulderAngle, elbowAngle);
  return Object.freeze({
    requestedTarget,
    target: clampedTarget,
    shoulderAngle: normalizeAngle(result.shoulderAngle),
    elbowAngle: normalizeAngle(result.elbowAngle),
    elbow: result.elbow,
    wrist: result.wrist,
    error: distance(result.wrist, requestedTarget),
    reachable,
    clamped: !reachable,
    requestedDistance,
    minimumDistance,
    maximumDistance,
    candidates: candidates.map(({ shoulderAngle: candidateShoulder, elbowAngle: candidateElbow, valid: candidateValid, preferenceScore }) => ({ shoulderAngle: normalizeAngle(candidateShoulder), elbowAngle: normalizeAngle(candidateElbow), valid: candidateValid, preferenceScore })),
  });
}

export function angleBetweenPoints(from, to) {
  const a = point(from, "from"); const b = point(to, "to");
  return Math.atan2(b.y - a.y, b.x - a.x);
}

export function angleDelta(from, to) {
  return normalizeAngle(to - from);
}
