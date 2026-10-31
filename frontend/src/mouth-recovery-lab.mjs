import { LayeredCharacterRenderer, LayeredCharacterRig } from "./layered-character.ts";
import { validateCharacterPack } from "./character-pack.mjs";

export const MOUTH_RECOVERY_STATES = Object.freeze(["closed", "slight", "moderate", "open", "smile"]);
const ROOT = "assets/mouth-recovery-lab";
const SOURCE_SIZE = Object.freeze([640, 720]);
const mouthAsset = (state) => `${ROOT}/mouth-${state}.svg`;

export const MOUTH_RECOVERY_LAB_PACK = Object.freeze({
  format: "fabuloom.character/0.1",
  rig_profile: "animation-ready/0.1",
  id: "mouth-recovery-lab-v1",
  name: "Mouth Recovery Lab V1",
  character: "prototype",
  language: "pt-BR",
  art_status: "technical-prototype",
  layers: [
    { id: "head", role: "head", asset: `${ROOT}/head.svg`, parent: null, anchor: [0.5, 0.5], position: [0.5, 0.5], size: [1, 1], source_size: [...SOURCE_SIZE], z: 0 },
    { id: "mouth", role: "mouth", asset: mouthAsset("closed"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.5], size: [1, 1], source_size: [...SOURCE_SIZE], mouth_motion: "subtle", z: 1 },
  ],
  facial_states: { mouth: Object.fromEntries(MOUTH_RECOVERY_STATES.map((state) => [state, mouthAsset(state)])) },
  expressions: [{ id: "neutral", overrides: {} }, { id: "smile", overrides: { mouth: mouthAsset("smile") } }],
  bindings: { mouth_open: "mouth" },
});

function stateForAmplitude(amplitude) {
  const value = Math.max(0, Math.min(1, Number(amplitude) || 0));
  if (value < 0.12) return "closed";
  if (value < 0.34) return "slight";
  if (value < 0.68) return "moderate";
  return "open";
}

export function createMouthRecoveryRenderer(canvas) {
  validateCharacterPack(MOUTH_RECOVERY_LAB_PACK);
  const rig = new LayeredCharacterRig();
  let renderer;
  renderer = new LayeredCharacterRenderer(canvas, rig, MOUTH_RECOVERY_LAB_PACK, {
    assetRoot: document.baseURI,
    renderBackground: false,
    assetResolver: (layer, pose, expressionAsset) => {
      if (layer.id !== "mouth") return expressionAsset;
      if (renderer.expression === "smile") return MOUTH_RECOVERY_LAB_PACK.facial_states.mouth.smile;
      return MOUTH_RECOVERY_LAB_PACK.facial_states.mouth[stateForAmplitude(pose.mouth_open)] || expressionAsset;
    },
  });
  return renderer;
}

export function renderMouthRecoveryState(renderer, state, timeMs = 0) {
  if (!MOUTH_RECOVERY_STATES.includes(state)) throw new Error(`unknown mouth recovery state: ${state}`);
  renderer.setExpression(state === "smile" ? "smile" : "neutral");
  const amplitude = { closed: 0, slight: 0.2, moderate: 0.5, open: 0.86, smile: 0 }[state];
  renderer.renderFrame({ timeMs, speechAmplitude: amplitude, isPlaying: state !== "closed" && state !== "smile" });
  return renderer.canvas;
}
