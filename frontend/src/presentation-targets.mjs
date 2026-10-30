/**
 * Provider- and character-independent presentation target contract.
 *
 * Coordinates are deliberately explicit:
 * - normalized-stage: x/y in [0, 1] relative to the composition canvas;
 * - stage-px: pixels in the composition canvas;
 * - scene-object: an object id resolved through the caller's scene registry.
 *
 * A target describes what the presenter should indicate. The presenter rig is
 * responsible for choosing a comfortable wrist position; the target is not
 * treated as a demand that the hand physically touch the object.
 */

export const PRESENTATION_TARGET_FORMAT = "fabuloom.presentation-target/0.1";
export const PRESENTATION_COORDINATE_SPACES = Object.freeze([
  "normalized-stage",
  "stage-px",
  "scene-object",
]);

const coordinateSpaces = new Set(PRESENTATION_COORDINATE_SPACES);
const identifierPattern = /^[A-Za-z][A-Za-z0-9_-]{1,63}$/;
const finite = (value) => typeof value === "number" && Number.isFinite(value);
const plainObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

function valid(condition, message) {
  if (!condition) throw new TypeError(message);
}

function finitePoint(value, label) {
  valid(plainObject(value) && finite(value.x) && finite(value.y), `${label} must contain finite x and y`);
  return { x: value.x, y: value.y };
}

function validateBounds(bounds, label = "bounds") {
  if (bounds === undefined || bounds === null) return undefined;
  valid(plainObject(bounds) && finite(bounds.x) && finite(bounds.y) && finite(bounds.width) && finite(bounds.height), `${label} must contain finite x, y, width and height`);
  valid(bounds.width >= 0 && bounds.height >= 0, `${label} dimensions must be non-negative`);
  return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
}

/** Validate and return a target without mutating it. */
export function validatePresentationTarget(target) {
  valid(plainObject(target), "Presentation target must be an object");
  valid(target.format === PRESENTATION_TARGET_FORMAT, "Unsupported presentation target format");
  valid(typeof target.id === "string" && identifierPattern.test(target.id), "Invalid presentation target id");
  valid(coordinateSpaces.has(target.coordinateSpace), "Unsupported presentation target coordinate space");
  const position = finitePoint(target.position, "Presentation target position");
  if (target.coordinateSpace === "normalized-stage") {
    valid(position.x >= 0 && position.x <= 1 && position.y >= 0 && position.y <= 1, "Normalized presentation target position must be in [0,1]");
  }
  if (target.coordinateSpace === "scene-object") valid(typeof target.objectId === "string" && target.objectId.length > 0, "Scene-object target requires objectId");
  if (target.label !== undefined) valid(typeof target.label === "string", "Presentation target label must be a string");
  const bounds = validateBounds(target.bounds);
  return Object.freeze({
    format: PRESENTATION_TARGET_FORMAT,
    id: target.id,
    position,
    coordinateSpace: target.coordinateSpace,
    label: target.label || target.id,
    objectId: target.objectId || null,
    ...(bounds ? { bounds } : {}),
  });
}

export function createPresentationTarget({ id, position, coordinateSpace = "normalized-stage", label = id, objectId = null, bounds } = {}) {
  return validatePresentationTarget({ format: PRESENTATION_TARGET_FORMAT, id, position, coordinateSpace, label, objectId, bounds });
}

function objectFromRegistry(registry, id) {
  if (!registry) return null;
  if (registry instanceof Map) return registry.get(id) || null;
  if (plainObject(registry)) return registry[id] || null;
  return null;
}

function pointToPixels(position, coordinateSpace, width, height) {
  return coordinateSpace === "normalized-stage"
    ? { x: position.x * width, y: position.y * height }
    : { x: position.x, y: position.y };
}

function boundsToPixels(bounds, coordinateSpace, width, height) {
  if (!bounds) return undefined;
  if (coordinateSpace === "normalized-stage") return {
    x: bounds.x * width,
    y: bounds.y * height,
    width: bounds.width * width,
    height: bounds.height * height,
  };
  return { ...bounds };
}

function centerOf(bounds) {
  return bounds ? { x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2 } : null;
}

/** Resolve a target to stage pixels while retaining its source metadata. */
export function resolvePresentationTarget(target, { width = 1080, height = 1920, objects } = {}) {
  valid(finite(width) && width > 0 && finite(height) && height > 0, "Presentation stage dimensions must be positive and finite");
  const validated = validatePresentationTarget(target);
  let coordinateSpace = validated.coordinateSpace;
  let position = validated.position;
  let bounds = validated.bounds;
  let objectId = validated.objectId;
  if (coordinateSpace === "scene-object") {
    const sceneObject = objectFromRegistry(objects, objectId);
    valid(sceneObject, `Presentation scene object not found: ${objectId}`);
    coordinateSpace = sceneObject.coordinateSpace || "normalized-stage";
    valid(coordinateSpaces.has(coordinateSpace) && coordinateSpace !== "scene-object", "Scene object coordinate space must be normalized-stage or stage-px");
    position = sceneObject.position || position;
    bounds = sceneObject.bounds || bounds;
  }
  const positionPx = pointToPixels(finitePoint(position, "Resolved target position"), coordinateSpace, width, height);
  const boundsPx = boundsToPixels(validateBounds(bounds, "Resolved target bounds"), coordinateSpace, width, height);
  const resolvedPoint = centerOf(boundsPx) || positionPx;
  return Object.freeze({
    target: validated,
    point: Object.freeze(resolvedPoint),
    position: Object.freeze(positionPx),
    bounds: boundsPx ? Object.freeze(boundsPx) : null,
    normalized: Object.freeze({ x: resolvedPoint.x / width, y: resolvedPoint.y / height }),
    width,
    height,
    coordinateSpace,
    objectId,
    label: validated.label,
  });
}

export function targetDirection(from, to) {
  const a = finitePoint(from, "Direction origin");
  const b = finitePoint(to, "Direction target");
  return Math.atan2(b.y - a.y, b.x - a.x);
}
