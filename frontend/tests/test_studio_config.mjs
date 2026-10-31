import test from "node:test";
import assert from "node:assert/strict";
import {
  DEV_LINKS,
  OFFICIAL_NARRATORS,
  PRODUCTION_EXPORTS,
  STUDIO_UI_FORMAT,
  STUDIO_SECTIONS,
  officialNarratorById,
  validateStudioSection,
} from "../src/studio-config.mjs";

test("Studio UI contract exposes stable and experimental sections", () => {
  assert.equal(STUDIO_UI_FORMAT, "fabuloom.studio-ui/0.1");
  assert.ok(STUDIO_SECTIONS.some((section) => section.id === "dashboard" && section.status === "stable"));
  assert.ok(STUDIO_SECTIONS.some((section) => section.id === "script" && section.status === "experimental"));
  assert.equal(validateStudioSection("preview"), "preview");
});

test("official narrators keep Santa V5 as the primary reference", () => {
  assert.equal(officialNarratorById("santa").voiceId, "pm_santa");
  assert.equal(officialNarratorById("santa").status, "production");
  assert.equal(officialNarratorById("dora").status, "awaiting-art-approval");
  assert.equal(officialNarratorById("alex").status, "awaiting-art-approval");
  assert.equal(OFFICIAL_NARRATORS.length, 3);
  assert.ok(DEV_LINKS.every((link) => link.href.startsWith("/")));
});

test("production export catalog contains only local workspace URLs", () => {
  assert.ok(PRODUCTION_EXPORTS.length >= 3);
  assert.ok(PRODUCTION_EXPORTS.every((item) => item.href.startsWith("/exports/")));
  assert.throws(() => validateStudioSection("unknown"), /Unknown Studio section/);
});
