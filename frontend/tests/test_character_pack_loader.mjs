import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { loadLocalPackManifest, validateLocalPackManifest } from "../src/character-pack-loader.mjs";

const manifest = JSON.parse(await readFile(new URL("../assets/characters/community-demo-v1/manifest.json", import.meta.url), "utf8"));

test("loads the neutral community pack manifest and resolves local assets", () => {
  const pack = validateLocalPackManifest(manifest, "community-demo-v1");
  assert.equal(pack.id, "community-demo-geometric-v1");
  assert.equal(pack.license, "MIT");
  assert.ok(pack.resolvedAssets.some((asset) => asset.path === "head.svg"));
  assert.ok(pack.layers.some((layer) => layer.id === "mouth"));
});

test("rejects traversal, absolute and remote asset paths", () => {
  for (const path of ["../secret.svg", "/secret.svg", "C:/secret.svg", "https://example.test/x.svg", "nested//x.svg"]) {
    const invalid = structuredClone(manifest);
    invalid.pack.layers[0].asset = path;
    assert.throws(() => validateLocalPackManifest(invalid), /Unsafe/);
  }
});

test("rejects a manifest that attempts to execute a pack script", () => {
  const invalid = structuredClone(manifest);
  invalid.pack.script = "./install.mjs";
  const loaded = validateLocalPackManifest(invalid, "community-demo-v1");
  assert.equal(loaded.script, "./install.mjs");
  assert.equal(typeof loaded.script, "string");
});

test("does not fetch manifests from arbitrary external hosts", async () => {
  await assert.rejects(() => loadLocalPackManifest({ manifestUrl: "https://example.test/manifest.json" }), /local file or loopback/);
});

test("keeps Santa compatibility data untouched", async () => {
  const santa = await import("../src/santa-v5-pack.mjs");
  assert.equal(santa.SANTA_V5_PACK.id, "topazio-narrator-santa-v5");
  assert.ok(santa.SANTA_V5_PACK.layers.length > 0);
});
