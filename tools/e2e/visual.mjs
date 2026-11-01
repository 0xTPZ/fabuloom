import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import { mkdir, mkdtemp, writeFile, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const repo = path.resolve(import.meta.dirname, "../..");
const evidence = await mkdtemp(path.join(os.tmpdir(), "fabuloom-visual-052-"));
const workspace = path.join(evidence, "workspace");
const framesDir = path.join(evidence, "canvas");
const ffmpeg = "ffmpeg";
await mkdir(workspace, { recursive: true }); await mkdir(framesDir, { recursive: true });
const port = 18767; const python = path.join(repo, ".venv", "Scripts", "python.exe");
const defaultHf = path.join(process.env.USERPROFILE || os.homedir(), ".cache", "huggingface");
const env = { ...process.env, FABULOOM_WORKSPACE_ROOT: workspace };
if (existsSync(path.join(defaultHf, "hub", "models--hexgrad--Kokoro-82M"))) env.HF_HOME = defaultHf;
const server = spawn(python, [path.join(repo, "frontend", "server.py"), "--port", String(port)], { cwd: repo, env, stdio: ["ignore", "pipe", "pipe"] });
const logs = []; server.stdout.on("data", (x) => logs.push(String(x))); server.stderr.on("data", (x) => logs.push(String(x)));
async function waitServer() { for (let i = 0; i < 80; i += 1) { try { if ((await fetch(`http://127.0.0.1:${port}/api/health`)).ok) return; } catch {} await new Promise((r) => setTimeout(r, 100)); } throw new Error("server timeout"); }
function tool(command, args) { return spawnSync(command, args, { encoding: "utf8", windowsHide: true }); }
function raw(command, args) { return spawnSync(command, args, { windowsHide: true }).stdout || Buffer.alloc(0); }
function frameRgb(file) { return raw(ffmpeg, ["-v", "error", "-i", file, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]); }
function metrics(a, b) { const n = Math.min(a.length, b.length); let sum = 0; let sq = 0; let changed = 0; for (let i = 0; i < n; i += 1) { const d = Math.abs(a[i] - b[i]); sum += d; sq += d * d; if (d > 12) changed += 1; } return { mae: sum / Math.max(1, n), rmse: Math.sqrt(sq / Math.max(1, n)), changed_ratio: changed / Math.max(1, n), bytes_a: a.length, bytes_b: b.length }; }
function writePngDataUrl(data, file) { return writeFile(file, Buffer.from(data.split(",")[1], "base64")); }

let browser;
const result = { classification: "BLOCKED", evidence, scenarios: [], logs };
try {
  await waitServer();
  browser = await chromium.launch({ headless: true, executablePath: existsSync("C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe") ? "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" : undefined });
  const page = await browser.newPage(); await page.goto(`http://127.0.0.1:${port}/studio.html`);
  await page.locator('[data-route="projects"]').first().click(); await page.locator("#new-project-button").click();
  await page.locator("#new-project-title").fill("Visual parity 052"); await page.locator("#new-project-description").fill("Projeto determinístico de auditoria Canvas e FFmpeg."); await page.locator("#project-dialog-submit").click();
  await page.locator("#script-title").waitFor(); await page.locator("#script-title").fill("Visual parity 052");
  await page.locator("#script-text").fill("Cena estática. Cena com zoom. Cena com pan horizontal. Cena com pan vertical."); await page.locator("#save-project-button").click(); await page.locator('[data-route="scenes"]').click();
  const sources = ["scene-00-t0.png", "scene-01-t0.png", "scene-02-t0.png", "scene-03-t0.png"].map((name) => path.join(repo, "workspace", "audit-0301", "frames", name));
  const pngs = [];
  const dimensions = ["1920:1080", "900:1600", "1200:1200", "1920:1080"];
  for (let i = 0; i < sources.length; i += 1) { const png = path.join(evidence, `source-${i}.png`); const converted = tool(ffmpeg, ["-y", "-i", sources[i], "-vf", `scale=${dimensions[i]}`, png]); if (converted.status !== 0) throw new Error(`source conversion failed: ${converted.stderr}`); pngs.push(png); }
  const cameras = ["static", "zoom", "pan-horizontal", "pan-vertical"];
  for (let i = 0; i < 4; i += 1) { const input = page.locator('#scene-list input[type="file"]').nth(i); await input.setInputFiles(pngs[i]); await page.locator('#scene-list img').nth(i).waitFor(); await page.locator("#scene-editor-camera").selectOption(cameras[i]); await page.locator("#scene-save-button").click(); }
  const listed = (await (await page.request.get(`http://127.0.0.1:${port}/api/projects`)).json()).projects.find((p) => p.title === "Visual parity 052");
  const savedProject = await (await page.request.get(`http://127.0.0.1:${port}/api/projects/${listed.id}`)).json();
  savedProject.scenes = savedProject.scenes.map((scene, index) => ({ ...scene, camera: cameras[index], duration_ms: 3000 }));
  await page.request.post(`http://127.0.0.1:${port}/api/projects/${listed.id}/save`, { data: { script: savedProject.script, scenes: savedProject.scenes } });
  await page.reload(); await page.waitForFunction(() => document.querySelector("#script-title")?.value === "Visual parity 052"); await page.locator('[data-route="preview"]').first().click();
  await page.locator('[data-route="audio"]').click(); await page.locator("#generate-narration-button").click();
  for (let i = 0; i < 300; i += 1) { const status = await page.locator("#save-label").innerText(); if (/Narração Santa V5 concluída|Narração bloqueada/i.test(status)) break; await new Promise((r) => setTimeout(r, 1000)); }
  if (!/Narração Santa V5 concluída/i.test(await page.locator("#save-label").innerText())) throw new Error("real narration did not complete");
  await page.locator('[data-route="preview"]').first().click(); await page.locator("#preview-mode-cinematic").click();
  const points = [0, 750, 1500, 2250, 2966]; const canvasFrames = [];
  for (let scene = 0; scene < 4; scene += 1) for (let point = 0; point < points.length; point += 1) { const globalMs = scene * 3000 + (scene > 0 && point === 0 ? 1 : points[point]); const data = await page.evaluate((ms) => window.__fabuloomVisualCapture(ms), globalMs); const file = path.join(framesDir, `scene-${String(scene).padStart(2, "0")}-p${point}.png`); await writePngDataUrl(data, file); canvasFrames.push({ scene, point, globalMs, file }); }
  await page.locator('[data-route="export"]').first().click(); await page.locator("#export-project-button").click();
  for (let i = 0; i < 180; i += 1) { const status = await page.locator("#export-status").innerText(); if (/concluído|bloqueada|falha/i.test(status)) break; await new Promise((r) => setTimeout(r, 1000)); }
  const project = (await (await page.request.get(`http://127.0.0.1:${port}/api/projects`)).json()).projects.find((p) => p.title === "Visual parity 052");
  const mp4 = path.join(workspace, project.exports.at(-1).path.replaceAll("/", path.sep)); const probe = tool("ffprobe", ["-v", "error", "-show_format", "-show_streams", "-of", "json", mp4]); const metadata = JSON.parse(probe.stdout); const duration = Number(metadata.format.duration); const valid = [];
  for (const item of canvasFrames) { if (item.globalMs / 1000 >= duration) continue; const extracted = path.join(evidence, `ffmpeg-scene-${String(item.scene).padStart(2, "0")}-p${item.point}.png`); const out = tool(ffmpeg, ["-y", "-ss", (item.globalMs / 1000).toFixed(3), "-i", mp4, "-frames:v", "1", "-q:v", "2", extracted]); const m = metrics(frameRgb(item.file), frameRgb(extracted)); valid.push({ ...item, extracted, status: out.status, metrics: m }); }
  result.mp4 = mp4; result.ffprobe = metadata; result.comparisons = valid; result.logs = logs; result.classification = valid.length === canvasFrames.length && valid.every((x) => x.status === 0 && x.metrics.changed_ratio < 0.08) ? "PASS" : "PARTIAL";
} catch (error) { result.error = String(error.stack || error); } finally { await writeFile(path.join(evidence, "metrics.json"), JSON.stringify(result, null, 2)); await writeFile(path.join(evidence, "report.html"), `<!doctype html><meta charset="utf-8"><title>Visual parity 052</title><h1>Visual parity 052</h1><p>${result.classification}</p><p>${evidence}</p>`); if (browser) await browser.close().catch(() => {}); server.kill(); }
console.log(JSON.stringify(result, null, 2));
if (result.classification === "FAIL") process.exitCode = 1;
