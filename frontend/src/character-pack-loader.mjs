import { validateCharacterPack } from "./character-pack.mjs";

const PACK_MANIFEST = "manifest.json";
const SAFE_ID = /^[a-z][a-z0-9_-]{1,63}$/;

function safeRelativePath(value) {
  return typeof value === "string"
    && value.length > 0
    && !value.startsWith("/")
    && !/^[A-Za-z]:/.test(value)
    && !value.includes("\\")
    && !value.includes(":")
    && !value.split("/").includes("..")
    && !value.includes("//");
}

function joinRoot(root, relative) {
  if (!safeRelativePath(relative)) throw new TypeError(`Unsafe local pack path: ${relative}`);
  const cleanRoot = String(root || "").replace(/[\\/]$/, "");
  return cleanRoot ? `${cleanRoot}/${relative}` : relative;
}

/** Validate a data-only manifest and resolve all assets below one local root. */
export function validateLocalPackManifest(manifest, root = "") {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) throw new TypeError("Pack manifest must be an object");
  if (!SAFE_ID.test(manifest.id || "")) throw new TypeError("Invalid pack manifest id");
  const pack = validateCharacterPack(manifest.pack || manifest);
  const assetPaths = new Set();
  const add = (path) => { if (!safeRelativePath(path)) throw new TypeError(`Unsafe local pack path: ${path}`); assetPaths.add(path); };
  for (const layer of pack.layers) add(layer.asset);
  for (const expression of pack.expressions) for (const path of Object.values(expression.overrides || {})) add(path);
  for (const path of assetPaths) joinRoot(root, path);
  return Object.freeze({
    ...pack,
    manifest: Object.freeze({ id: manifest.id, version: manifest.version || pack.version || "0.1.0", root: String(root || "") }),
    resolvedAssets: Object.freeze([...assetPaths].map((path) => Object.freeze({ path, url: joinRoot(root, path) }))),
  });
}

/** Load JSON only; no module/script from a pack is ever imported or evaluated. */
export async function loadLocalPackManifest({ manifestUrl, root = "" } = {}) {
  if (!manifestUrl || typeof manifestUrl !== "string" || !/^file:/i.test(manifestUrl)) {
    let local = false;
    try {
      const url = new URL(manifestUrl);
      local = url.protocol === "http:" && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
    } catch { /* report the same safe error below */ }
    if (!local) throw new TypeError("manifestUrl must be a local file or loopback URL");
  }
  const response = await fetch(manifestUrl);
  if (!response.ok) throw new Error(`Unable to read character pack manifest (${response.status})`);
  return validateLocalPackManifest(await response.json(), root);
}

/** Discover manifests from a File System Access directory without executing pack content. */
export async function discoverLocalPacks(directoryHandle) {
  if (!directoryHandle || typeof directoryHandle.values !== "function") throw new TypeError("A local directory handle is required");
  const discovered = [];
  for await (const entry of directoryHandle.values()) {
    if (entry.kind !== "directory") continue;
    const manifest = await entry.getFileHandle(PACK_MANIFEST).then((handle) => handle.getFile()).then((file) => file.text()).then(JSON.parse).catch(() => null);
    if (!manifest) continue;
    discovered.push(validateLocalPackManifest(manifest, entry.name));
  }
  return Object.freeze(discovered);
}

/** Build a pack from a directory input without exposing the selected files to a server. */
export async function loadLocalPackFiles(files, { maxFiles = 128, maxBytes = 25 * 1024 * 1024 } = {}) {
  const list = [...(files || [])];
  if (!list.length) throw new Error("Nenhum arquivo foi selecionado");
  if (list.length > maxFiles) throw new Error(`Pack excede o limite de ${maxFiles} arquivos`);
  if (list.reduce((sum, file) => sum + (file.size || 0), 0) > maxBytes) throw new Error("Pack excede o limite de 25 MB");
  const manifestFile = list.find((file) => file.name === "manifest.json" || file.webkitRelativePath?.endsWith("/manifest.json"));
  if (!manifestFile) throw new Error("O diretório precisa conter manifest.json");
  const manifest = JSON.parse(await manifestFile.text());
  const prefix = manifestFile.webkitRelativePath ? manifestFile.webkitRelativePath.split("/").slice(0, -1).join("/") : "";
  const byPath = new Map(list.map((file) => [file.webkitRelativePath ? file.webkitRelativePath.split("/").slice(prefix ? prefix.split("/").length : 0).join("/") : file.name, file]));
  const pack = validateLocalPackManifest(manifest, "");
  const assetUrls = Object.fromEntries(pack.resolvedAssets.map(({ path }) => {
    const file = byPath.get(path);
    if (!file) throw new Error(`Asset ausente no pack: ${path}`);
    return [path, URL.createObjectURL(file)];
  }));
  return Object.freeze({ pack, assetUrls });
}
