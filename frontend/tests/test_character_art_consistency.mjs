import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";
import test from "node:test";
import {
  ALEX_NARRATOR_PACK_CARTOON_V1,
  DORA_NARRATOR_PACK_CARTOON_V1,
  TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1,
} from "../src/topazio-narrator-packs-cartoon-v1.mjs";

const root = new URL("../", import.meta.url);
const local = (asset) => new URL(asset, root).pathname.replace(/^\/+/, "").replaceAll("/", "\\");

test("cartoon narrator packs preserve distinct voices and the shared contract", () => {
  assert.equal(TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.format, "fabuloom.narrator-cartoon/0.1");
  assert.equal(TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.source_size[0], 1254);
  assert.equal(DORA_NARRATOR_PACK_CARTOON_V1.voice_id, "pf_dora");
  assert.equal(ALEX_NARRATOR_PACK_CARTOON_V1.voice_id, "pm_alex");
  assert.equal(DORA_NARRATOR_PACK_CARTOON_V1.language, "pt-BR");
  assert.equal(ALEX_NARRATOR_PACK_CARTOON_V1.language, "pt-BR");
  assert.notEqual(DORA_NARRATOR_PACK_CARTOON_V1.layers[0].asset, ALEX_NARRATOR_PACK_CARTOON_V1.layers[0].asset);
});

test("cartoon packs use one identity base and compact explicit mouth states", () => {
  for (const pack of [DORA_NARRATOR_PACK_CARTOON_V1, ALEX_NARRATOR_PACK_CARTOON_V1]) {
    assert.deepEqual(pack.layers.map((layer) => layer.id), ["head", "eyelids", "mouth"]);
    assert.deepEqual(Object.keys(pack.facial_states.mouth), ["closed", "slight", "moderate", "open", "smile"]);
    assert.deepEqual(pack.layers[0].source_size, [1254, 1254]);
    assert.equal(pack.layers[1].parent, "head");
    assert.equal(pack.layers[2].parent, "head");
    assert.equal(pack.layers[2].mouth_motion, "subtle");
    for (const asset of [pack.layers[0].asset, pack.layers[1].asset, ...Object.values(pack.facial_states.mouth)]) {
      const path = local(asset);
      assert.ok(existsSync(path), `missing ${asset}`);
      assert.ok(statSync(path).size > 100, `empty ${asset}`);
    }
    for (const state of Object.values(pack.facial_states.mouth)) {
      const svg = readFileSync(local(state), "utf8");
      assert.match(svg, /viewBox="0 0 1254 1254"/);
      assert.doesNotMatch(svg, /<rect[^>]+width="1254"/);
      assert.match(svg, /stroke=/);
    }
  }
});
