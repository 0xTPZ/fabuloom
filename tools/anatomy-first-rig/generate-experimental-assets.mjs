import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { decodePng, encodePng } from "../visual-inspector/png.mjs";

const sourceRoot = path.resolve("E:/Fabuloom/studio/frontend/assets/characters/topazio-narrators-v5/santa");
const outputRoot = path.resolve("E:/Fabuloom/studio/frontend/assets/characters/topazio-narrators-v5/experimental-anatomy");

function keepBand(input, topRatio, bottomRatio, featherRatio = 0.055) {
  const image = decodePng(input);
  const top = Math.floor(image.height * topRatio);
  const bottom = Math.ceil(image.height * bottomRatio);
  const rgba = Buffer.from(image.rgba);
  for (let y = 0; y < image.height; y += 1) {
    const distanceFromEdge = Math.min(y - top, bottom - 1 - y);
    const feather = Math.max(1, image.height * featherRatio);
    const alphaScale = y < top || y >= bottom ? 0 : Math.min(1, distanceFromEdge / feather);
    if (alphaScale >= 1) continue;
    for (let x = 0; x < image.width; x += 1) {
      const offset = (y * image.width + x) * 4 + 3;
      rgba[offset] = Math.round(rgba[offset] * alphaScale);
    }
  }
  return encodePng({ width: image.width, height: image.height, rgba });
}

async function writeBand(name, source, topRatio, bottomRatio) {
  const target = path.join(outputRoot, name);
  await writeFile(target, keepBand(await readFile(path.join(sourceRoot, source)), topRatio, bottomRatio));
  return { name, source, topRatio, bottomRatio, target };
}

await mkdir(outputRoot, { recursive: true });
const generated = [
  await writeBand("upper-arm-left-anatomy.png", "upper-arm-left.png", 0.04, 0.70),
  await writeBand("upper-arm-right-anatomy.png", "upper-arm-right.png", 0.04, 0.70),
  await writeBand("forearm-left-anatomy.png", "forearm-left.png", 0.23, 0.93),
  await writeBand("forearm-right-anatomy.png", "forearm-right.png", 0.23, 0.93),
  await writeBand("cuff-left-anatomy.png", "forearm-left.png", 0.69, 0.98),
  await writeBand("cuff-right-anatomy.png", "forearm-right.png", 0.69, 0.98),
];
await writeFile(path.join(outputRoot, "README.md"), [
  "# Santa V5 experimental anatomy-first layers",
  "",
  "These files are an isolated Mission 015 experiment derived from the approved V5 raster layers.",
  "They are masked bands, not replacements for the official pack: the original files remain under `../santa/`.",
  "The experiment uses feathered alpha edges to avoid rectangular cut lines and tests whether reducing duplicated shoulder/cuff volume improves rigid-layer articulation before any redrawing or mesh migration.",
  "",
].join("\n"), "utf8");
console.log(JSON.stringify(generated, null, 2));
