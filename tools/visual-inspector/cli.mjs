#!/usr/bin/env node

import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  VISUAL_INSPECTION_FORMAT,
  defaultInspectionConfig,
  diagnoseFrame,
  diagnoseMotion,
  summarizeInspection,
} from "../../frontend/src/visual-inspector-core.mjs";
import { comparePngBuffers } from "./png.mjs";

const TOOL_VERSION = "1.0.0";
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const studioRoot = path.resolve(scriptDirectory, "..", "..");
const defaultWorkspaceOutput = path.resolve("E:/Fabuloom/workspace/exports/visual-inspector");

function argumentValue(args, name, fallback = null) {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
}

function hasArgument(args, name) { return args.includes(name); }

function executablePath() {
  const candidates = [
    process.env.FABULOOM_EDGE,
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  ].filter(Boolean);
  return candidates.find((candidate) => existsSync(candidate)) || null;
}

function pythonPath() {
  const candidate = "E:/Fabuloom/workspace/.venv/Scripts/python.exe";
  return existsSync(candidate) ? candidate : "python";
}

function runProcess(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { ...options, windowsHide: true });
    let stderr = "";
    child.stderr?.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", reject);
    child.on("close", (code, signal) => resolve({ code, signal, stderr }));
  });
}

async function waitForServer(url, timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The local server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 120));
  }
  throw new Error(`local server did not become ready: ${url}`);
}

async function readJsonEventually(file, timeoutMs = 5000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      return JSON.parse(await readFile(file, "utf8"));
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error(`capture report was not written: ${file}`);
}

function captureSpecs() {
  return [
    { name: "neutral", mode: "neutral", timeMs: 0, close: "full", sequence: null },
    { name: "face-close", mode: "neutral", timeMs: 0, close: "face", sequence: null },
    { name: "blink", mode: "blink", timeMs: 4330, close: "face", sequence: null },
    { name: "mouth-open", mode: "mouth", timeMs: 1200, close: "face", speechAmplitude: 0.92, sequence: null },
    { name: "hands-neutral", mode: "neutral", timeMs: 0, close: "full", sequence: null },
    { name: "wave-rest", mode: "wave", timeMs: 0, close: "full", sequence: "WAVE_HELLO" },
    { name: "wave-raised", mode: "wave", timeMs: 1680, close: "full", sequence: "WAVE_HELLO" },
    { name: "wave-return", mode: "wave", timeMs: 4600, close: "full", sequence: "WAVE_HELLO" },
    { name: "point-rest", mode: "point", timeMs: 0, close: "full", sequence: "POINT_AT" },
    { name: "point-hold", mode: "point", timeMs: 5200, close: "full", sequence: "POINT_AT" },
    { name: "feet-neutral", mode: "neutral", timeMs: 0, close: "full", sequence: null },
  ];
}

function relativePath(root, file) { return path.relative(root, file).replaceAll("\\", "/"); }

function markdownReport(report) {
  const lines = [
    "# Fabuloom Visual Inspector V1",
    "",
    `- Formato: \`${report.format}\``,
    `- Ferramenta: \`${report.tool.name} ${report.tool.version}\``,
    `- Character: \`${report.character.id}\``,
    `- Renderer: \`${report.tool.renderer}\``,
    `- Backend de captura: \`${report.tool.captureBackend}\``,
    `- Status: **${report.summary.status}**`,
    "",
    "## Resumo",
    "",
    `- Erros: ${report.summary.counts.error}`,
    `- Avisos: ${report.summary.counts.warning}`,
    `- Hipóteses: ${report.summary.counts.hypothesis}`,
    `- Capturas: ${report.captures.length}`,
    "",
    "A comparação automática usa o quadro neutro da mesma execução como baseline quando nenhuma referência externa é fornecida. Isso demonstra a mecânica de comparação, mas não declara aprovação artística.",
    "",
    "## Capturas",
    "",
    "| Quadro | Tempo | Modo | Arquivo | Diagnóstico |\n| --- | ---: | --- | --- | --- |",
  ];
  for (const capture of report.captures) {
    const diagnostics = capture.frame ? report.frameDiagnostics.find((entry) => entry.frameTimeMs === capture.frame.timeMs && entry.capture === capture.name) : null;
    lines.push(`| ${capture.name} | ${capture.frame?.timeMs ?? "—"} ms | ${capture.frame?.captureMode || "erro"} | \`${capture.screenshot}\` | ${diagnostics?.issues.length || (capture.error ? "falha" : 0)} ocorrência(s) |`);
  }
  lines.push("", "## Ocorrências", "", "| Severidade | Confiança | Código | Mensagem |", "| --- | --- | --- | --- |");
  const allIssues = [...report.frameDiagnostics.flatMap((entry) => entry.issues || []), ...report.motionDiagnostics.flatMap((entry) => entry.issues || [])];
  if (!allIssues.length) lines.push("| — | — | — | Nenhum problema verificável encontrado nesta execução. |");
  for (const finding of allIssues) lines.push(`| ${finding.severity} | ${finding.confidence} | \`${finding.code}\` | ${finding.message} |`);
  lines.push("", "## Comparações", "", "| Comparação | Razão de diferença | Bounds | Máscara | Overlay |", "| --- | ---: | --- | --- | --- |");
  if (!report.comparisons.length) lines.push("| — | — | Nenhuma comparação executada. |");
  for (const comparison of report.comparisons) {
    lines.push(`| ${comparison.name} | ${comparison.differenceRatio === null ? "incompatível" : comparison.differenceRatio.toFixed(4)} | ${comparison.differenceBounds ? JSON.stringify(comparison.differenceBounds) : "—"} | \`${comparison.diffMask}\` | \`${comparison.overlay}\` |`);
  }
  lines.push("", "## Política de correção", "", "O Inspector não modifica código, assets ou parâmetros. Uma correção deve ser aplicada pelo fluxo do Codex em uma branch isolada, seguida por nova captura, testes e comparação.");
  return `${lines.join("\n")}\n`;
}

async function main() {
  const args = process.argv.slice(2);
  if (hasArgument(args, "--help")) {
    console.log("Usage: node tools/visual-inspector/cli.mjs [--output DIR] [--reference PNG] [--port PORT]");
    return;
  }
  const edge = executablePath();
  if (!edge) throw new Error("Microsoft Edge headless was not found; install nothing globally, use --help only after providing FABULOOM_EDGE to an approved local executable.");
  const output = path.resolve(argumentValue(args, "--output", defaultWorkspaceOutput));
  const port = Number(argumentValue(args, "--port", "8786"));
  const referencePath = argumentValue(args, "--reference", null);
  const session = `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const captureRoot = path.join(output, "captures");
  const comparisonRoot = path.join(output, "comparisons");
  await mkdir(captureRoot, { recursive: true });
  await mkdir(comparisonRoot, { recursive: true });
  const server = spawn(pythonPath(), ["frontend/server.py", "--port", String(port)], {
    cwd: studioRoot,
    env: { ...process.env, FABULOOM_CAPTURE_DIR: captureRoot },
    windowsHide: true,
    stdio: ["ignore", "ignore", "pipe"],
  });
  let serverError = "";
  server.stderr?.on("data", (chunk) => { serverError += chunk.toString(); });
  try {
    await waitForServer(`http://127.0.0.1:${port}/visual-inspector-capture.html`);
    const captures = [];
    for (const spec of captureSpecs()) {
      const screenshotFile = path.join(output, `${spec.name}.png`);
      const params = new URLSearchParams({
        session,
        file: `${spec.name}.json`,
        mode: spec.mode,
        timeMs: String(spec.timeMs),
        close: spec.close,
        width: spec.close === "face" ? "680" : "680",
        height: spec.close === "face" ? "520" : "1140",
      });
      if (spec.speechAmplitude) params.set("speechAmplitude", String(spec.speechAmplitude));
      const url = `http://127.0.0.1:${port}/visual-inspector-capture.html?${params}`;
      const result = await runProcess(edge, ["--headless", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw", "--window-size=680,1140", "--virtual-time-budget=7000", `--screenshot=${screenshotFile}`, url], { cwd: studioRoot });
      const payload = await readJsonEventually(path.join(captureRoot, session, `${spec.name}.json`));
      if (!payload.frame) {
        captures.push({ ...spec, screenshot: relativePath(output, screenshotFile), error: payload.error || result.stderr || serverError });
        continue;
      }
      captures.push({ ...spec, screenshot: relativePath(output, screenshotFile), frame: payload.frame, edgeExit: result.code });
    }
    const frameDiagnostics = captures.filter((capture) => capture.frame).map((capture) => ({ capture: capture.name, ...diagnoseFrame(capture.frame, defaultInspectionConfig()) }));
    const motionDiagnostics = [];
    for (const sequence of ["WAVE_HELLO", "POINT_AT"]) {
      const frames = captures.filter((capture) => capture.sequence === sequence && capture.frame).map((capture) => capture.frame);
      if (frames.length) motionDiagnostics.push({ sequence, ...diagnoseMotion(frames, defaultInspectionConfig()) });
    }
    const comparisons = [];
    const neutral = captures.find((capture) => capture.name === "neutral");
    const externalReference = referencePath ? await readFile(referencePath) : null;
    const referenceBuffer = externalReference || (neutral ? await readFile(path.join(output, "neutral.png")) : null);
    const comparisonTargets = captures.filter((capture) => ["blink", "mouth-open", "wave-raised", "point-hold"].includes(capture.name));
    for (const target of comparisonTargets) {
      if (!referenceBuffer) continue;
      const currentBuffer = await readFile(path.join(output, `${target.name}.png`));
      const result = comparePngBuffers(referenceBuffer, currentBuffer, { colorTolerance: 12, alphaTolerance: 8 });
      const baseName = referencePath ? `reference-vs-${target.name}` : `neutral-vs-${target.name}`;
      const diffMask = path.join(comparisonRoot, `${baseName}-diff-mask.png`);
      const overlay = path.join(comparisonRoot, `${baseName}-overlay.png`);
      if (result.compatible) {
        await writeFile(diffMask, result.diffMaskPng);
        await writeFile(overlay, result.overlayPng);
      }
      comparisons.push({ name: baseName, differenceRatio: result.differenceRatio, meanChannelDifference: result.meanChannelDifference, differenceBounds: result.differenceBounds, diffMask: relativePath(output, diffMask), overlay: relativePath(output, overlay), compatible: result.compatible, reason: result.reason || null });
    }
    const captureErrors = captures.filter((capture) => capture.error).map((capture) => `${capture.name}: ${capture.error}`);
    const summary = summarizeInspection({ frameDiagnostics, motionDiagnostics, captureErrors });
    const report = {
      format: VISUAL_INSPECTION_FORMAT,
      generatedAt: new Date().toISOString(),
      tool: { name: "Fabuloom Visual Inspector", version: TOOL_VERSION, renderer: "SantaV5SceneRenderer → LayeredCharacterRenderer", captureBackend: "Microsoft Edge headless over loopback HTTP", imageComparator: "built-in PNG RGBA comparator" },
      character: { id: "topazio-narrator-santa-v5", voiceId: "pm_santa", packFormat: "fabuloom.character/0.1" },
      reference: { path: referencePath ? path.resolve(referencePath) : null, mode: referencePath ? "external-png" : "same-run-neutral-baseline", note: referencePath ? "External reference was supplied by the caller." : "Neutral frame is a diagnostic baseline, not approved-art authority." },
      captures: captures.map((capture) => ({ name: capture.name, mode: capture.mode, timeMs: capture.timeMs, sequence: capture.sequence, screenshot: capture.screenshot, frame: capture.frame || null, error: capture.error || null })),
      frameDiagnostics,
      motionDiagnostics,
      comparisons,
      summary,
    };
    await writeFile(path.join(output, "visual-inspection-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    await writeFile(path.join(output, "visual-inspection-report.md"), markdownReport(report), "utf8");
    console.log(JSON.stringify({ output, status: summary.status, counts: summary.counts, captures: captures.length, report: path.join(output, "visual-inspection-report.json") }, null, 2));
    if (summary.status === "needs-correction") process.exitCode = 2;
  } finally {
    server.kill();
  }
}

main().catch((error) => {
  console.error(`[visual-inspector] ${error.stack || error}`);
  process.exitCode = 1;
});
