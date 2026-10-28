/**
 * Fabuloom Layered Character Contract v0.1.
 * Data-only representation: no TTS, Canvas, or private Animus dependencies.
 * Coordinates and pivots use normalized [0,1] canvas space.
 */
export const CHARACTER_FORMAT = "fabuloom.character/0.1";
const idPattern = /^[a-z][a-z0-9_-]{1,63}$/;
const safeAsset = /^(?!\/)(?![A-Za-z]:)(?!.*(?:^|\/)\.\.(?:\/|$))(?!.*\\)(?!.*:)(?!\/\/)[a-zA-Z0-9_./-]+\.(?:png|webp|svg)$/;
const channels = new Set(["head_rotation","eye_open","mouth_open","breathing","left_arm","right_arm","hair_sway","expression"]);
function valid(condition, message) { if (!condition) throw new TypeError(message); }
function identifier(id, label) { valid(typeof id === "string" && idPattern.test(id), `Invalid ${label}`); }
function unit(value, label) { valid(typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1, `Invalid ${label}: expected [0,1]`); }
function point(value, label) { valid(Array.isArray(value) && value.length === 2, `Invalid ${label}`); value.forEach((n,i)=>unit(n,`${label}[${i}]`)); }
function plainObject(value) { return value !== null && typeof value === "object" && !Array.isArray(value); }
/**
 * Validate external character descriptors before loading any sprite resource.
 * Reject unknown versions; never evaluate code or fetch remote URLs from a pack.
 */
export function validateCharacterPack(pack) {
  valid(plainObject(pack), "Character pack must be an object");
  valid(pack.format === CHARACTER_FORMAT, "Unsupported character pack format");
  identifier(pack.id,"character id");
  valid(typeof pack.name === "string" && pack.name.trim().length > 0, "Missing name");
  valid(Array.isArray(pack.layers) && pack.layers.length > 0 && pack.layers.length <= 128,"Invalid layer count");
  valid(Array.isArray(pack.expressions), "Missing expressions");
  valid(plainObject(pack.bindings), "Missing animation bindings");
  const ids = new Set();
  for (const layer of pack.layers) {
    valid(plainObject(layer), "Invalid layer");
    identifier(layer.id,"layer id");
    valid(!ids.has(layer.id), "Duplicate layer id");
    ids.add(layer.id);
    valid(typeof layer.asset === "string" && safeAsset.test(layer.asset) && !layer.asset.includes("//"), "Unsafe sprite path");
    if (layer.parent !== null) identifier(layer.parent,"layer parent");
    point(layer.anchor,"layer anchor");
    point(layer.position,"layer position");
    if (layer.size !== undefined) point(layer.size,"layer size");
    valid(Number.isInteger(layer.z) && layer.z >= -1000 && layer.z <= 1000,"Invalid z index");
  }
  for (const layer of pack.layers) {
    valid(layer.parent === null || ids.has(layer.parent),"Unknown parent layer");
    let current = layer;
    const visited = new Set([current.id]);
    while (current.parent !== null) {
      valid(!visited.has(current.parent),"Layer hierarchy cycle");
      visited.add(current.parent);
      current = pack.layers.find(l=>l.id===current.parent);
    }
  }
  const expressionIds = new Set();
  for (const expression of pack.expressions) {
    valid(plainObject(expression),"Invalid expression");
    identifier(expression.id,"expression id");
    valid(!expressionIds.has(expression.id),"Duplicate expression");
    expressionIds.add(expression.id);
    valid(plainObject(expression.overrides),"Invalid expression overrides");
    for (const [layerId, asset] of Object.entries(expression.overrides)) {
      valid(ids.has(layerId),"Unknown expression layer");
      valid(typeof asset === "string" && safeAsset.test(asset) && !asset.includes("//"),"Unsafe expression sprite path");
    }
  }
  for (const [channel, layerId] of Object.entries(pack.bindings)) {
    valid(channels.has(channel), "Unsupported animation channel");
    valid(typeof layerId === "string" && ids.has(layerId),"Unknown animation target");
  }
  return pack;
}
