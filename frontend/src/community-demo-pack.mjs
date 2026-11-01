export const COMMUNITY_DEMO_PACK = Object.freeze({
  format: "fabuloom.character/0.1", id: "community-demo-geometric-v1", version: "1.0.0",
  name: "Ponto, demonstrador geométrico", author: "Fabuloom community demo", license: "MIT",
  source: "Original geometric demonstration authored for Fabuloom",
  compatibility: { renderer: "fabuloom.character/0.1" }, voice: { id: "", note: "No voice or model is bundled" },
  layers: [
    { id: "body", asset: "body.svg", parent: null, anchor: [0.5, 0.5], position: [0.5, 0.68], size: [0.55, 0.72], z: 0, role: "torso" },
    { id: "head", asset: "head.svg", parent: "body", anchor: [0.5, 0.5], position: [0.5, 0.25], size: [0.72, 0.72], z: 1, role: "head" },
    { id: "eyes", asset: "eyes.svg", parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.45], size: [0.55, 0.12], z: 2, role: "eyes" },
    { id: "mouth", asset: "mouth.svg", parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.68], size: [0.28, 0.12], z: 3, role: "mouth" }
  ],
  expressions: [{ id: "neutral", overrides: {} }, { id: "smile", overrides: { mouth: "mouth-smile.svg" } }],
  bindings: { head_rotation: "head", eye_open: "eyes", mouth_open: "mouth", breathing: "body" },
});
