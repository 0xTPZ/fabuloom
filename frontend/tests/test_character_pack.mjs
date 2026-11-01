import test from "node:test";
import assert from "node:assert/strict";
import { CHARACTER_FORMAT, validateCharacterPack } from "../src/character-pack.mjs";

const base = () => ({
  format: CHARACTER_FORMAT, id: "narrator-one", name: "Narrator",
  layers: [
    { id: "body", asset: "assets/body.webp", parent: null, anchor: [0.5,0.5], position: [0.5,0.7], z: 0 },
    { id: "head", asset: "assets/head.webp", parent: "body", anchor: [0.5,0.8], position: [0.5,0.3], z: 1 },
    { id: "mouth", asset: "assets/mouth.png", parent: "head", anchor: [0.5,0.5], position: [0.5,0.7], z: 2 }
  ],
  expressions: [{ id: "neutral", overrides: {} }, { id: "happy", overrides: { mouth: "assets/mouth-happy.png" } }],
  bindings: { head_rotation: "head", mouth_open: "mouth", breathing: "body" }
});

test("valid layered character passes", () => assert.equal(validateCharacterPack(base()).name,"Narrator"));
test("rejects unsupported format", () => { const p=base(); p.format="v2"; assert.throws(()=>validateCharacterPack(p)); });
test("rejects duplicate nodes", () => { const p=base(); p.layers[1].id="body"; assert.throws(()=>validateCharacterPack(p),/Duplicate/); });
test("rejects unknown parent", () => { const p=base(); p.layers[1].parent="missing"; assert.throws(()=>validateCharacterPack(p),/parent/); });
test("rejects parent cycle", () => { const p=base(); p.layers[0].parent="mouth"; assert.throws(()=>validateCharacterPack(p),/cycle/); });
test("rejects traversal and remote assets", () => {
  for (const asset of ["../secret.png","https://remote.test/x.png","C:/secret.png","\\\\server\\share.png","assets//x.png"]) {
    const p=base(); p.layers[0].asset=asset; assert.throws(()=>validateCharacterPack(p),asset);
  }
});
test("rejects invalid numeric pivots", () => {
  for(const n of [NaN,Infinity,-0.1,1.1]) { const p=base(); p.layers[0].anchor[0]=n; assert.throws(()=>validateCharacterPack(p)); }
});
test("validates optional normalized layer size", () => {
  const p=base(); p.layers[0].size=[0.8,0.9]; assert.equal(validateCharacterPack(p).layers[0].size[0],0.8);
  p.layers[0].size=[1.1,0.9]; assert.throws(()=>validateCharacterPack(p),/layer size/);
});
test("rejects unsupported animation target", () => { const p=base(); p.bindings.mouth_open="absent"; assert.throws(()=>validateCharacterPack(p)); });
test("rejects expression overriding absent layer", () => { const p=base(); p.expressions[0].overrides={nope:"assets/a.png"}; assert.throws(()=>validateCharacterPack(p)); });
test("accepts the additive animation-ready profile and roles", () => {
  const p = base();
  p.rig_profile = "animation-ready/0.1";
  p.layers[0].role = "torso";
  p.layers[1].role = "head";
  p.layers[2].role = "mouth";
  assert.equal(validateCharacterPack(p).rig_profile, "animation-ready/0.1");
});
test("rejects unknown animation-ready profile or role", () => {
  const p = base();
  p.rig_profile = "animation-ready/9.0";
  assert.throws(() => validateCharacterPack(p), /rig profile/);
  const q = base();
  q.layers[0].role = "wing";
  assert.throws(() => validateCharacterPack(q), /layer role/);
});
