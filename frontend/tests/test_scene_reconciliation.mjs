import assert from "node:assert/strict";
import test from "node:test";
import { reconcileSceneDrafts } from "../src/scene-reconciliation.mjs";

const old = [
  { id: "scene-001", text: "A", image: "a.png", camera: "zoom", duration_ms: 4100, transition: "cut" },
  { id: "scene-002", text: "B", image: "b.png", camera: "pan-horizontal", duration_ms: 3200, transition: "cut" },
  { id: "scene-003", text: "C", image: "c.png", camera: "pan-vertical", duration_ms: 2800, transition: "cut" },
];

test("inserting in the middle preserves exact-text identities and assets", () => {
  const result = reconcileSceneDrafts(old, ["A", "NEW", "B", "C"], (i) => `new-${i}`);
  assert.deepEqual(result.scenes.map((scene) => scene.id), ["scene-001", "new-1", "scene-002", "scene-003"]);
  assert.deepEqual(result.scenes.map((scene) => scene.image), ["a.png", null, "b.png", "c.png"]);
});

test("editing text with unchanged cardinality keeps identity and configuration", () => {
  const result = reconcileSceneDrafts(old, ["A edited", "B", "C"]);
  assert.equal(result.scenes[0].id, "scene-001");
  assert.equal(result.scenes[0].camera, "zoom");
  assert.equal(result.scenes[0].image, "a.png");
});

test("deletion reports removed scenes instead of redistributing their assets", () => {
  const result = reconcileSceneDrafts(old, ["A", "C"]);
  assert.deepEqual(result.scenes.map((scene) => scene.id), ["scene-001", "scene-003"]);
  assert.deepEqual(result.removed.map((scene) => scene.id), ["scene-002"]);
});

test("split and join create safe new scenes when correspondence is ambiguous", () => {
  const split = reconcileSceneDrafts([{ id: "scene-001", text: "A B", image: "ab.png" }], ["A", "B"], (i) => `new-${i}`);
  assert.deepEqual(split.scenes.map((scene) => scene.id), ["new-0", "new-1"]);
  assert.equal(split.scenes.every((scene) => scene.image === null), true);
  const joined = reconcileSceneDrafts(old, ["A B C"]);
  assert.equal(joined.scenes[0].image, null);
  assert.equal(joined.removed.length, 3);
});

test("duplicate texts never use position to redistribute assets", () => {
  const duplicate = [{ id: "scene-001", text: "Refrão", image: "one.png" }, { id: "scene-002", text: "Refrão", image: "two.png" }];
  const result = reconcileSceneDrafts(duplicate, ["Refrão", "Refrão"]);
  assert.deepEqual(result.scenes.map((scene) => scene.image), [null, null]);
  assert.equal(result.removed.length, 2);
});

test("one edited scene can use the remaining one-to-one match", () => {
  const result = reconcileSceneDrafts(old, ["A editada", "B", "C"]);
  assert.equal(result.scenes[0].id, "scene-001");
  assert.equal(result.scenes[0].image, "a.png");
  assert.equal(result.scenes[1].id, "scene-002");
});

test("full replacement does not inherit the old project's assets", () => {
  const result = reconcileSceneDrafts(old, ["Nova 1", "Nova 2", "Nova 3"]);
  assert.equal(result.scenes.every((scene) => scene.image === null), true);
  assert.equal(result.removed.length, 3);
});
