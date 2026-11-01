import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readdir, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";

const repo = path.resolve(import.meta.dirname, "../..");
const evidence = await mkdtemp(path.join(os.tmpdir(), "fabuloom-e2e-047-"));
const workspace = path.join(evidence, "workspace");
await mkdir(workspace, { recursive: true });
const port = 18765;
const python = path.join(repo, ".venv", "Scripts", "python.exe");
const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
let server;
const logs = [];
const defaultHfHome = path.join(process.env.USERPROFILE || os.homedir(), ".cache", "huggingface");
const hfHome = process.env.HF_HOME || (existsSync(path.join(defaultHfHome, "hub", "models--hexgrad--Kokoro-82M")) ? defaultHfHome : undefined);
const serverEnv = { ...process.env, FABULOOM_WORKSPACE_ROOT: workspace };
if (hfHome) serverEnv.HF_HOME = hfHome;
function startServer() {
  server = spawn(python, [path.join(repo, "frontend", "server.py"), "--port", String(port)], { cwd: repo, env: serverEnv, stdio: ["ignore", "pipe", "pipe"] });
  server.stdout.on("data", (chunk) => logs.push({ stream: "stdout", text: String(chunk) }));
  server.stderr.on("data", (chunk) => logs.push({ stream: "stderr", text: String(chunk) }));
}
startServer();
async function waitForServer() { for (let i = 0; i < 50; i += 1) { try { const response = await fetch(`http://127.0.0.1:${port}/api/health`); if (response.ok) return; } catch {} await new Promise((resolve) => setTimeout(resolve, 100)); } throw new Error("test server did not start"); }
const result = { classification: "FAIL", evidence, flows: [], logs };
const exportMode = process.argv.includes("--export");

async function findFiles(root, suffix) {
  const found = [];
  for (const entry of await readdir(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) found.push(...await findFiles(full, suffix));
    else if (!suffix || entry.name.toLowerCase().endsWith(suffix)) found.push(full);
  }
  return found;
}

function runTool(command, args) {
  const processResult = spawnSync(command, args, { encoding: "utf8", windowsHide: true });
  return { status: processResult.status, stdout: processResult.stdout || "", stderr: processResult.stderr || "" };
}
let browser;
try {
  await waitForServer();
  browser = await chromium.launch({ headless: true, executablePath: existsSync(edge) ? edge : undefined });
  const context = await browser.newContext({ acceptDownloads: false });
  const page = await context.newPage();
  await page.goto(`http://127.0.0.1:${port}/studio.html`);
  await page.locator('[data-route="projects"]').first().click();
  await page.locator("#new-project-button").click();
  await page.locator("#new-project-title").fill("E2E-Ponto");
  await page.locator("#new-project-description").fill("Projeto descartável de teste automatizado.");
  await page.locator("#project-dialog-submit").click();
  await page.locator("#script-title").waitFor({ state: "visible", timeout: 10000 });
  await page.locator("#script-title").fill("E2E-Ponto");
  await page.locator("#script-text").fill("Ponto atravessa a ponte e encontra uma luz.");
  await page.locator("#save-project-button").click();
  await page.locator('[data-route="scenes"]').click();
  const sceneImage = path.join(repo, "frontend/assets/characters/fantasy-narrator/torso-core.png");
  await page.locator('#scene-list input[type="file"]').first().setInputFiles(sceneImage);
  await page.locator('#scene-list img').first().waitFor({ timeout: 5000 });
  await page.locator("#scene-editor-camera").selectOption("zoom");
  await page.locator("#scene-save-button").click();
  await page.locator('[data-route="narrators"]').first().click();
  await page.getByRole("button", { name: /Ponto, demonstrador geométrico/ }).click();
  await page.getByText(/Ponto, demonstrador geométrico selecionado e salvo/).waitFor({ timeout: 10000 });
  await page.locator("#studio-character-expression").selectOption("smile");
  let expressionStatus = "";
  for (let attempt = 0; attempt < 50; attempt += 1) { expressionStatus = await page.locator("#studio-character-library-status").innerText(); if (/Expressão smile salva|não salva/.test(expressionStatus)) break; await new Promise((resolve) => setTimeout(resolve, 100)); }
  if (!/Expressão smile salva/.test(expressionStatus)) throw new Error(`expression persistence failed: ${expressionStatus}`);
  await page.screenshot({ path: path.join(evidence, "studio-project-saved.png"), fullPage: true });
  result.flows.push({ name: "Studio create/script/scene/image/movement/save", status: "PASS" });
  result.flows.push({ name: "Ponto select/expression/project association", status: "PASS" });
  await context.close();
  await browser.close(); browser = null;
  server.kill();
  await new Promise((resolve) => setTimeout(resolve, 300));
  startServer();
  await waitForServer();
  // New browser context, no localStorage/session reuse.
  browser = await chromium.launch({ headless: true, executablePath: existsSync(edge) ? edge : undefined });
  const fresh = await browser.newContext(); const reopened = await fresh.newPage();
  await reopened.goto(`http://127.0.0.1:${port}/studio.html`);
  await reopened.locator('[data-route="projects"]').first().click();
  await reopened.getByRole("heading", { name: "E2E-Ponto", exact: true }).waitFor();
  await reopened.getByRole("button", { name: "Abrir produção →" }).first().click();
  await reopened.locator('[data-route="scenes"]').click();
  await reopened.locator("#scene-list .scene-editor-row").first().waitFor({ timeout: 5000 });
  const restoredText = await reopened.locator("#scene-list").innerText();
  const restoredImage = await reopened.locator('#scene-list img').count();
  const restoredProject = restoredText.includes("Ponto atravessa") && restoredImage > 0;
  result.flows.push({ name: "Project survives new browser context", status: restoredProject ? "PASS" : "FAIL" });
  await reopened.locator('[data-route="narrators"]').first().click();
  let restoredExpression = ""; let restoredPack = "";
  for (let attempt = 0; attempt < 50; attempt += 1) { restoredExpression = await reopened.locator("#studio-character-expression").inputValue(); restoredPack = await reopened.locator("#studio-character-library-status").innerText(); if (/restaurado do projeto|indisponível/.test(restoredPack)) break; await new Promise((resolve) => setTimeout(resolve, 100)); }
  const packRestored = restoredExpression === "smile" && /restaurado do projeto/.test(restoredPack);
  result.flows.push({ name: "Ponto/pack/expression restored in Studio", status: packRestored ? "PASS" : "FAIL" });
  const project = await reopened.request.get(`http://127.0.0.1:${port}/api/projects`);
  const projectData = (await project.json()).projects.find((item) => item.title === "E2E-Ponto");
  result.debug = { restoredExpression, restoredPack, projectData };
  result.flows.push({ name: "Backend project_pack reference", status: projectData?.character_pack?.expression === "smile" ? "PASS" : "FAIL" });
  if (exportMode) {
    await reopened.locator('[data-route="audio"]').first().click();
    await reopened.locator("#generate-narration-button").click();
    let audioStatus = "";
    let operationStatus = "";
    for (let attempt = 0; attempt < 300; attempt += 1) { operationStatus = await reopened.locator("#save-label").innerText(); audioStatus = await reopened.locator("#audio-voice-state").innerText(); if (/Narração Santa V5 concluída|Narração bloqueada/i.test(operationStatus)) break; await new Promise((resolve) => setTimeout(resolve, 1000)); }
    if (!/Narração Santa V5 concluída/i.test(operationStatus)) {
      result.flows.push({ name: "Real narration through Studio button", status: "BLOCKED", note: audioStatus || "Kokoro did not complete" });
      result.classification = "BLOCKED";
    } else {
      result.flows.push({ name: "Real narration through Studio button", status: "PASS" });
      await reopened.locator('[data-route="export"]').first().click();
      await reopened.locator("#export-project-button").click();
      let exportStatus = "";
      for (let attempt = 0; attempt < 180; attempt += 1) { exportStatus = await reopened.locator("#export-status").innerText(); if (/concluído|bloqueada|falha/i.test(exportStatus)) break; await new Promise((resolve) => setTimeout(resolve, 1000)); }
      const mp4Files = await findFiles(workspace, ".mp4");
      if (!/concluído/i.test(exportStatus) || !mp4Files.length) {
        result.flows.push({ name: "MP4 export through Studio button", status: "FAIL", note: exportStatus, files: mp4Files });
      } else {
        const mp4 = mp4Files.at(-1); const probe = runTool("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", mp4]); const decode = runTool("ffmpeg", ["-v", "error", "-i", mp4, "-f", "null", "-"]); let metadata = null; try { metadata = JSON.parse(probe.stdout); } catch {}
        const video = metadata?.streams?.find((stream) => stream.codec_type === "video"); const audio = metadata?.streams?.find((stream) => stream.codec_type === "audio");
        result.export = { path: mp4, status: exportStatus, ffprobe: probe, decode, video, audio };
        const valid = probe.status === 0 && decode.status === 0 && video?.codec_name === "h264" && audio?.codec_name === "aac";
        result.flows.push({ name: "MP4/FFprobe/FFmpeg validation", status: valid ? "PASS" : "FAIL", path: mp4 });
        result.classification = valid ? "PARTIAL" : "FAIL";
      }
    }
  }
  await reopened.screenshot({ path: path.join(evidence, "reopened.png"), fullPage: true });
  if (!exportMode) result.classification = restoredProject ? "PARTIAL" : "FAIL";
  result.notes = "The real Studio project and Ponto character-pack flow are automated. Native Windows dialog, MP4/FFprobe, and Canvas×FFmpeg remain outside this run.";
  await fresh.close();
} catch (error) { result.error = String(error.stack || error); }
finally { if (browser) await browser.close().catch(() => {}); server.kill(); await writeFile(path.join(evidence, "result.json"), JSON.stringify(result, null, 2)); await writeFile(path.join(evidence, "report.html"), `<!doctype html><meta charset="utf-8"><title>Fabuloom E2E 047</title><h1>Fabuloom E2E 047</h1><p>Classification: <strong>${result.classification}</strong></p><ul>${result.flows.map((flow) => `<li>${flow.name}: ${flow.status}</li>`).join("")}</ul><p>Evidence: ${result.evidence}</p>`); }
console.log(JSON.stringify(result, null, 2));
if (result.classification === "FAIL") process.exitCode = 1;
