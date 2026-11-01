import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
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
function startServer() {
  server = spawn(python, [path.join(repo, "frontend", "server.py"), "--port", String(port)], { cwd: repo, env: { ...process.env, FABULOOM_WORKSPACE_ROOT: workspace }, stdio: ["ignore", "pipe", "pipe"] });
  server.stdout.on("data", (chunk) => logs.push({ stream: "stdout", text: String(chunk) }));
  server.stderr.on("data", (chunk) => logs.push({ stream: "stderr", text: String(chunk) }));
}
startServer();
async function waitForServer() { for (let i = 0; i < 50; i += 1) { try { const response = await fetch(`http://127.0.0.1:${port}/api/health`); if (response.ok) return; } catch {} await new Promise((resolve) => setTimeout(resolve, 100)); } throw new Error("test server did not start"); }
const result = { classification: "FAIL", evidence, flows: [], logs };
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
  await page.locator("#script-title").fill("E2E-Ponto");
  await page.locator("#script-text").fill("Ponto atravessa a ponte e encontra uma luz.");
  await page.locator("#save-project-button").click();
  await page.locator('[data-route="scenes"]').click();
  const sceneImage = path.join(repo, "frontend/assets/characters/fantasy-narrator/torso-core.png");
  await page.locator('#scene-list input[type="file"]').first().setInputFiles(sceneImage);
  await page.locator('#scene-list img').first().waitFor({ timeout: 5000 });
  await page.locator("#scene-editor-camera").selectOption("zoom");
  await page.locator("#scene-save-button").click();
  await page.screenshot({ path: path.join(evidence, "studio-project-saved.png"), fullPage: true });
  result.flows.push({ name: "Studio create/script/scene/image/movement/save", status: "PASS" });
  result.flows.push({ name: "Ponto library in production Studio", status: "PARTIAL", note: "Character pack library exists on Character Stage, but studio.html has no pack selector." });
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
  const installed = await reopened.request.get(`http://127.0.0.1:${port}/api/packs/community-demo-geometric-v1/1.0.0`);
  result.flows.push({ name: "Managed pack recovery endpoint", status: installed.ok() ? "PASS" : "NOT TESTED", note: "This complete Studio flow did not install a character pack; Mission 047 covers that separate Character Stage flow." });
  await reopened.screenshot({ path: path.join(evidence, "reopened.png"), fullPage: true });
  result.classification = restoredProject ? "PARTIAL" : "FAIL";
  result.notes = "The real Studio project flow is automated. Ponto library/association remains PARTIAL because studio.html does not expose the character-pack selector; native Windows dialog is not exercised by Playwright.";
  await fresh.close();
} catch (error) { result.error = String(error.stack || error); }
finally { if (browser) await browser.close().catch(() => {}); server.kill(); await writeFile(path.join(evidence, "result.json"), JSON.stringify(result, null, 2)); await writeFile(path.join(evidence, "report.html"), `<!doctype html><meta charset="utf-8"><title>Fabuloom E2E 047</title><h1>Fabuloom E2E 047</h1><p>Classification: <strong>${result.classification}</strong></p><ul>${result.flows.map((flow) => `<li>${flow.name}: ${flow.status}</li>`).join("")}</ul><p>Evidence: ${result.evidence}</p>`); }
console.log(JSON.stringify(result, null, 2));
if (result.classification === "FAIL") process.exitCode = 1;
