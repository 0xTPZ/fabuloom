import { readdir } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "../../frontend/tests");
const proprietary = new Set([
  "test_character_art_consistency.mjs",
  "test_facial_recovery.mjs",
  "test_santa_v3.mjs",
  "test_santa_v4.mjs",
  "test_santa_v5_anatomy_experimental.mjs",
  "test_santa_v5_art.mjs",
  "test_topazio_narrators.mjs",
  "test_topazio_narrators_v3.mjs",
  "test_topazio_narrators_v4.mjs",
]);
const files = (await readdir(root)).filter((name) => name.endsWith(".mjs") && !proprietary.has(name)).map((name) => path.join(root, name));
const result = spawnSync(process.execPath, ["--test", ...files], { stdio: "inherit" });
process.exitCode = result.status ?? 1;
