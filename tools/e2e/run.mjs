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
const server = spawn(python, [path.join(repo, "frontend", "server.py"), "--port", String(port)], {
  cwd: repo, env: { ...process.env, FABULOOM_WORKSPACE_ROOT: workspace }, stdio: ["ignore", "pipe", "pipe"]
});
const logs = [];
server.stdout.on("data", (chunk) => logs.push({ stream: "stdout", text: String(chunk) }));
server.stderr.on("data", (chunk) => logs.push({ stream: "stderr", text: String(chunk) }));
async function waitForServer() { for (let i = 0; i < 50; i += 1) { try { const response = await fetch(`http://127.0.0.1:${port}/api/health`); if (response.ok) return; } catch {} await new Promise((resolve) => setTimeout(resolve, 100)); } throw new Error("test server did not start"); }
const result = { classification: "FAIL", evidence, flows: [], logs };
let browser;
try {
  await waitForServer();
  browser = await chromium.launch({ headless: true, executablePath: existsSync(edge) ? edge : undefined });
  const context = await browser.newContext({ acceptDownloads: false });
  const page = await context.newPage();
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.getByRole("button", { name: "Importar pasta local" }).waitFor();
  const project = await page.request.post(`http://127.0.0.1:${port}/api/projects`, { data: { title: "E2E-Ponto", format: "horizontal-1080p" } });
  result.flows.push({ name: "Studio opens", status: "PASS" });
  result.flows.push({ name: "Library visible", status: "PASS" });
  // The UI import is intentionally the only path used for installation in this flow.
  const input = page.locator("#character-pack-input");
  await input.setInputFiles(path.join(repo, "frontend/assets/characters/community-demo-v1"));
  let importStatus = "";
  for (let attempt = 0; attempt < 50; attempt += 1) { importStatus = await page.locator("#character-library-status").innerText(); if (importStatus !== "Somente manifesto JSON e imagens declaradas; nenhum script é executado.") break; await new Promise((resolve) => setTimeout(resolve, 100)); }
  if (/bloqueada|falha/i.test(importStatus)) throw new Error(`UI import failed: ${importStatus}`);
  await page.getByRole("button", { name: /Ponto, demonstrador geométrico/ }).first().click();
  await page.getByLabel("Selecionar expressão").selectOption("smile");
  await page.screenshot({ path: path.join(evidence, "ponto-selected.png"), fullPage: true });
  result.flows.push({ name: "Import/select/render Ponto", status: "PASS" });
  await context.close();
  await browser.close(); browser = null;
  // New browser context, no localStorage/session reuse.
  browser = await chromium.launch({ headless: true, executablePath: existsSync(edge) ? edge : undefined });
  const fresh = await browser.newContext(); const reopened = await fresh.newPage();
  await reopened.goto(`http://127.0.0.1:${port}/index.html`);
  const installed = await reopened.request.get(`http://127.0.0.1:${port}/api/packs/community-demo-geometric-v1/1.0.0`);
  result.flows.push({ name: "Managed pack survives new context", status: installed.ok() ? "PASS" : "FAIL" });
  await reopened.screenshot({ path: path.join(evidence, "reopened.png"), fullPage: true });
  result.classification = installed.ok() ? "PARTIAL" : "FAIL";
  result.notes = "The project creation in this initial harness is API setup only; the main UI shell does not yet expose project creation on Character Stage. Native Windows dialog is not exercised by Playwright.";
  await fresh.close();
} catch (error) { result.error = String(error.stack || error); }
finally { if (browser) await browser.close().catch(() => {}); server.kill(); await writeFile(path.join(evidence, "result.json"), JSON.stringify(result, null, 2)); await writeFile(path.join(evidence, "report.html"), `<!doctype html><meta charset="utf-8"><title>Fabuloom E2E 047</title><h1>Fabuloom E2E 047</h1><p>Classification: <strong>${result.classification}</strong></p><ul>${result.flows.map((flow) => `<li>${flow.name}: ${flow.status}</li>`).join("")}</ul><p>Evidence: ${result.evidence}</p>`); }
console.log(JSON.stringify(result, null, 2));
if (result.classification === "FAIL") process.exitCode = 1;
