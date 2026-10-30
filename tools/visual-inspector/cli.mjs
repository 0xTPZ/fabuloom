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
import { correctFaceDuplicateFixture, createKnownDefectFixtures, resolveFixtureRegion } from "./fixtures.mjs";
import { annotatePng, comparePngBuffers, decodePng } from "./png.mjs";

const TOOL_VERSION = "1.1.0";
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
    { name: "idle-rest", mode: "neutral", timeMs: 0, close: "full", sequence: "IDLE" },
    { name: "idle-mid", mode: "neutral", timeMs: 2000, close: "full", sequence: "IDLE" },
    { name: "idle-late", mode: "neutral", timeMs: 4000, close: "full", sequence: "IDLE" },
    { name: "face-close", mode: "neutral", timeMs: 0, close: "face", sequence: null },
    { name: "blink", mode: "blink", timeMs: 4330, close: "face", sequence: null },
    { name: "mouth-open", mode: "mouth", timeMs: 1200, close: "face", speechAmplitude: 0.92, sequence: null },
    { name: "hands-neutral", mode: "neutral", timeMs: 0, close: "full", sequence: null },
    { name: "wave-rest", mode: "wave", timeMs: 0, close: "full", sequence: "WAVE_HELLO" },
    { name: "wave-raised", mode: "wave", timeMs: 1680, close: "full", sequence: "WAVE_HELLO" },
    { name: "wave-return", mode: "wave", timeMs: 4600, close: "full", sequence: "WAVE_HELLO" },
    { name: "point-rest", mode: "point", timeMs: 0, close: "full", sequence: "POINT_AT" },
    { name: "point-approach", mode: "point", timeMs: 1000, close: "full", sequence: "POINT_AT" },
    { name: "point-hold", mode: "point", timeMs: 5200, close: "full", sequence: "POINT_AT" },
    { name: "feet-neutral", mode: "neutral", timeMs: 0, close: "full", sequence: null },
  ];
}

function relativePath(root, file) { return path.relative(root, file).replaceAll("\\", "/"); }

function frameRegionToScreenshot(frame, bounds, imageWidth, imageHeight) {
  if (!bounds) return null;
  const composition = frame.sceneComposition;
  if (composition) {
    const scaleX = imageWidth / Number(frame.captureCanvas?.width || imageWidth);
    const scaleY = imageHeight / Number(frame.captureCanvas?.height || imageHeight);
    return {
      left: (composition.characterX + bounds.left) * scaleX,
      top: (composition.characterY + bounds.top * composition.scaleY) * scaleY,
      right: (composition.characterX + bounds.right) * scaleX,
      bottom: (composition.characterY + bounds.bottom * composition.scaleY) * scaleY,
    };
  }
  const scaleX = imageWidth / Number(frame.canvas?.width || imageWidth);
  const scaleY = imageHeight / Number(frame.canvas?.height || imageHeight);
  return { left: bounds.left * scaleX, top: bounds.top * scaleY, right: bounds.right * scaleX, bottom: bounds.bottom * scaleY };
}

function fixtureRegionForIssue(fixture, frame, issue) {
  if (issue?.region?.kind === "bounds") return issue.region.bounds;
  if (issue?.region?.kind === "points") return issue.region.bounds;
  return resolveFixtureRegion(fixture, frame);
}

function evaluateFixture(fixture, config) {
  const diagnostic = fixture.frames ? diagnoseMotion(fixture.frames, config) : diagnoseFrame(fixture.frame, config);
  const issues = diagnostic.issues || [];
  const matchedCodes = fixture.expectedCodes.filter((code) => issues.some((finding) => finding.code === code));
  const missingCodes = fixture.expectedCodes.filter((code) => !matchedCodes.includes(code));
  const unexpectedCodes = [...new Set(issues.filter((finding) => !fixture.expectedCodes.includes(finding.code)).map((finding) => finding.code))];
  const matchedIssue = issues.find((finding) => fixture.expectedCodes.includes(finding.code));
  const locationLayers = new Set(fixture.regionSpec?.layers || []);
  const locationMatched = fixture.regionSpec?.kind === "landmarks"
    ? issues.some((finding) => fixture.regionSpec.landmarks.includes(finding.evidence?.landmarkId))
    : issues.some((finding) => (finding.relatedLayers || []).some((layerId) => locationLayers.has(layerId)));
  const severityMatched = issues.some((finding) => fixture.expectedCodes.includes(finding.code) && finding.severity === fixture.expectedSeverity);
  const frame = fixture.frame;
  return {
    id: fixture.id,
    label: fixture.label,
    defect: fixture.defect,
    expectedCodes: fixture.expectedCodes,
    expectedSeverity: fixture.expectedSeverity,
    detected: missingCodes.length === 0,
    matchedCodes,
    missingCodes,
    unexpectedCodes,
    severityMatched,
    regionMatched: locationMatched,
    falsePositiveCount: unexpectedCodes.length,
    falseNegative: missingCodes.length > 0,
    issues,
    region: resolveFixtureRegion(fixture, frame),
    regionSpec: fixture.regionSpec,
    notes: fixture.notes || "",
    frames: fixture.frames?.map((candidate) => candidate.timeMs) || [frame?.timeMs],
    representativeFrame: frame,
    matchedIssue,
  };
}

function fixtureMetrics(results) {
  const detected = results.filter((result) => result.detected).length;
  const falseNegatives = results.filter((result) => result.falseNegative).length;
  const falsePositives = results.reduce((sum, result) => sum + result.falsePositiveCount, 0);
  const severityMatches = results.filter((result) => result.severityMatched).length;
  const regionMatches = results.filter((result) => result.regionMatched).length;
  return {
    fixtures: results.length,
    detected,
    missed: falseNegatives,
    detectionRate: results.length ? detected / results.length : 0,
    falsePositiveCount: falsePositives,
    severityMatches,
    regionMatches,
    knownGoodFalsePositiveCount: 0,
  };
}

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
    "O baseline técnico é sempre o quadro neutro da mesma execução. Uma referência externa é tratada separadamente como referência artística; nenhuma das duas declara aprovação artística por si só.",
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
    lines.push(`| ${comparison.name} (${comparison.referenceKind}) | ${comparison.differenceRatio === null ? "incompatível" : comparison.differenceRatio.toFixed(4)} | ${comparison.differenceBounds ? JSON.stringify(comparison.differenceBounds) : "—"} | \`${comparison.diffMask}\` | \`${comparison.overlay}\` |`);
  }
  lines.push("", "## Fixtures de defeitos conhecidos", "", "| Fixture | Esperado | Detectado | Região | Falsos positivos | Evidência |", "| --- | --- | --- | --- | ---: | --- |");
  if (!report.fixtures?.length) lines.push("| — | — | — | — | — | Nenhuma fixture executada. |");
  for (const fixture of report.fixtures || []) {
    lines.push(`| ${fixture.id} | \`${fixture.expectedCodes.join(", ")}\` | ${fixture.detected ? "sim" : "não"} | ${fixture.regionMatched ? "correta" : "não confirmada"} | ${fixture.falsePositiveCount} | \`${fixture.evidenceImage || "—"}\` |`);
  }
  lines.push("", "## Métricas", "", `- Fixtures detectadas: ${report.fixtureMetrics?.detected || 0}/${report.fixtureMetrics?.fixtures || 0}`, `- Taxa de detecção: ${((report.fixtureMetrics?.detectionRate || 0) * 100).toFixed(1)}%`, `- Falsos positivos nas fixtures: ${report.fixtureMetrics?.falsePositiveCount || 0}`, `- Falsos positivos no quadro conhecido-good: ${report.fixtureMetrics?.knownGoodFalsePositiveCount || 0}`, `- Severidade correta: ${report.fixtureMetrics?.severityMatches || 0}/${report.fixtureMetrics?.fixtures || 0}`, `- Região compatível: ${report.fixtureMetrics?.regionMatches || 0}/${report.fixtureMetrics?.fixtures || 0}`);
  lines.push("", "## Ciclo de correção controlado", "", report.correction ? `A fixture ${report.correction.fixtureId} foi diagnosticada antes e depois da substituição controlada do asset preservado. Antes: ${report.correction.beforeCodes.join(", ") || "nenhum"}. Depois: ${report.correction.afterCodes.join(", ") || "nenhum"}. Assets oficiais não foram modificados.` : "Nenhum ciclo de correção foi executado.");
  lines.push("", "## Cobertura e limitações", "", "O relatório separa baseline técnico, referência artística, evidência insuficiente e revisão humana. A comparação de bounds alfa é conservadora e não substitui uma máscara alfa por pixel completa; o comparador PNG usa tolerância de cor/alpha. Análise por IA não foi executada nesta rodada.");
  lines.push("", "## Política de correção", "", "O Inspector não modifica código, assets ou parâmetros. Uma correção deve ser aplicada pelo fluxo do Codex em uma branch isolada, seguida por nova captura, testes e comparação.");
  return `${lines.join("\n")}\n`;
}

async function main() {
  const args = process.argv.slice(2);
  if (hasArgument(args, "--help")) {
    console.log("Usage: node tools/visual-inspector/cli.mjs [--output DIR] [--reference PNG] [--port PORT] [--variant production-v5|historical-head-original]");
    return;
  }
  const edge = executablePath();
  if (!edge) throw new Error("Microsoft Edge headless was not found; install nothing globally, use --help only after providing FABULOOM_EDGE to an approved local executable.");
  const output = path.resolve(argumentValue(args, "--output", defaultWorkspaceOutput));
  const port = Number(argumentValue(args, "--port", "8786"));
  const referencePath = argumentValue(args, "--reference", null);
  const variant = argumentValue(args, "--variant", "production-v5");
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
        height: spec.close === "face" ? "520" : "1920",
      });
      if (spec.speechAmplitude) params.set("speechAmplitude", String(spec.speechAmplitude));
      if (variant !== "production-v5") params.set("variant", variant);
      const url = `http://127.0.0.1:${port}/visual-inspector-capture.html?${params}`;
      const result = await runProcess(edge, ["--headless", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw", "--window-size=680,1920", "--virtual-time-budget=7000", `--screenshot=${screenshotFile}`, url], { cwd: studioRoot });
      const payload = await readJsonEventually(path.join(captureRoot, session, `${spec.name}.json`));
      if (!payload.frame) {
        captures.push({ ...spec, screenshot: relativePath(output, screenshotFile), error: payload.error || result.stderr || serverError });
        continue;
      }
      captures.push({ ...spec, screenshot: relativePath(output, screenshotFile), frame: payload.frame, edgeExit: result.code });
    }
    const frameDiagnostics = captures.filter((capture) => capture.frame).map((capture) => ({ capture: capture.name, ...diagnoseFrame(capture.frame, defaultInspectionConfig()) }));
    const motionDiagnostics = [];
    for (const sequence of ["IDLE", "WAVE_HELLO", "POINT_AT"]) {
      const frames = captures.filter((capture) => capture.sequence === sequence && capture.frame).map((capture) => capture.frame);
      if (frames.length) motionDiagnostics.push({ sequence, ...diagnoseMotion(frames, defaultInspectionConfig()) });
    }

    const neutral = captures.find((capture) => capture.name === "neutral");
    const neutralFrame = neutral?.frame || null;
    const fixtureRoot = path.join(output, "fixtures");
    await mkdir(fixtureRoot, { recursive: true });
    const fixtures = neutralFrame ? createKnownDefectFixtures(neutralFrame) : [];
    const fixtureResults = fixtures.map((fixture) => evaluateFixture(fixture, defaultInspectionConfig()));
    const knownGoodDiagnostics = neutralFrame ? diagnoseFrame(neutralFrame, defaultInspectionConfig()) : { issues: [] };
    const knownGoodFalsePositiveCount = knownGoodDiagnostics.issues.length;
    for (const result of fixtureResults) {
      const sourceBuffer = neutral ? await readFile(path.join(output, "neutral.png")) : null;
      if (!sourceBuffer || !result.region) continue;
      const screenshot = decodePng(sourceBuffer);
      const mapped = frameRegionToScreenshot(result.representativeFrame, result.region, screenshot.width, screenshot.height);
      const evidenceImage = path.join(fixtureRoot, `${result.id}-evidence.png`);
      await writeFile(evidenceImage, annotatePng(sourceBuffer, { regions: [mapped], color: [255, 70, 60, 255], lineWidth: 5 }));
      result.evidenceImage = relativePath(output, evidenceImage);
    }
    const fixtureMetricsReport = fixtureMetrics(fixtureResults);
    fixtureMetricsReport.knownGoodFalsePositiveCount = knownGoodFalsePositiveCount;
    const faceFixture = fixtures.find((fixture) => fixture.id === "face-painted-duplicate");
    const correctedFace = faceFixture && neutralFrame ? correctFaceDuplicateFixture(faceFixture, neutralFrame) : null;
    const correction = faceFixture && correctedFace ? {
      fixtureId: faceFixture.id,
      mode: "controlled-preserved-asset-fixture",
      beforeCodes: diagnoseFrame(faceFixture.frame, defaultInspectionConfig()).issues.map((finding) => finding.code),
      afterCodes: diagnoseFrame(correctedFace, defaultInspectionConfig()).issues.map((finding) => finding.code),
      verified: diagnoseFrame(correctedFace, defaultInspectionConfig()).issues.filter((finding) => finding.severity === "error").length === 0,
      note: "A correção substitui apenas o asset histórico da fixture por head-clean.png no JSON de teste; nenhum asset oficial foi alterado.",
    } : null;
    const comparisons = [];
    const externalReference = referencePath ? await readFile(referencePath) : null;
    const technicalReference = neutral ? await readFile(path.join(output, "neutral.png")) : null;
    const comparisonTargets = captures.filter((capture) => ["blink", "mouth-open", "wave-raised", "point-hold"].includes(capture.name));
    const addComparison = async (name, referenceBuffer, targetBuffer, referenceKind) => {
      if (!referenceBuffer || !targetBuffer) return;
      const result = comparePngBuffers(referenceBuffer, targetBuffer, { colorTolerance: 12, alphaTolerance: 8 });
      const diffMask = path.join(comparisonRoot, `${name}-diff-mask.png`);
      const overlay = path.join(comparisonRoot, `${name}-overlay.png`);
      if (result.compatible) {
        await writeFile(diffMask, result.diffMaskPng);
        await writeFile(overlay, result.overlayPng);
      }
      comparisons.push({ name, referenceKind, differenceRatio: result.differenceRatio, meanChannelDifference: result.meanChannelDifference, differenceBounds: result.differenceBounds, diffMask: relativePath(output, diffMask), overlay: relativePath(output, overlay), compatible: result.compatible, reason: result.reason || null });
    };
    for (const target of comparisonTargets) {
      if (!technicalReference) continue;
      const currentBuffer = await readFile(path.join(output, `${target.name}.png`));
      await addComparison(`technical-neutral-vs-${target.name}`, technicalReference, currentBuffer, "technical-baseline");
      if (externalReference) await addComparison(`artistic-reference-vs-${target.name}`, externalReference, currentBuffer, "artistic-reference");
    }
    if (externalReference && technicalReference) await addComparison("artistic-reference-vs-neutral", externalReference, technicalReference, "artistic-reference");
    const captureErrors = captures.filter((capture) => capture.error).map((capture) => `${capture.name}: ${capture.error}`);
    const summary = summarizeInspection({ frameDiagnostics, motionDiagnostics, captureErrors });
    const reportFixtures = fixtureResults.map(({ representativeFrame, matchedIssue, ...fixture }) => ({
      ...fixture,
      matchedIssue: matchedIssue ? { code: matchedIssue.code, severity: matchedIssue.severity, confidence: matchedIssue.confidence, relatedLayers: matchedIssue.relatedLayers, region: matchedIssue.region } : null,
    }));
    const report = {
      format: VISUAL_INSPECTION_FORMAT,
      generatedAt: new Date().toISOString(),
      tool: { name: "Fabuloom Visual Inspector", version: TOOL_VERSION, renderer: "SantaV5SceneRenderer → LayeredCharacterRenderer", captureBackend: "Microsoft Edge headless over loopback HTTP", imageComparator: "built-in PNG RGBA comparator" },
      character: { id: "topazio-narrator-santa-v5", voiceId: "pm_santa", packFormat: "fabuloom.character/0.1" },
      reference: {
        technicalBaseline: { mode: "same-run-neutral", capture: neutral?.name || null, path: neutral ? relativePath(output, path.join(output, "neutral.png")) : null },
        artisticReference: { provided: Boolean(referencePath), path: referencePath ? path.resolve(referencePath) : null, note: referencePath ? "External reference supplied by the caller; artistic review remains separate from technical change detection." : "No artistic reference supplied." },
        path: referencePath ? path.resolve(referencePath) : null,
        mode: referencePath ? "technical-and-artistic" : "technical-baseline-only",
        note: "The neutral frame detects same-run changes; it is not approval authority.",
      },
      captures: captures.map((capture) => ({ name: capture.name, mode: capture.mode, timeMs: capture.timeMs, sequence: capture.sequence, screenshot: capture.screenshot, frame: capture.frame || null, error: capture.error || null })),
      frameDiagnostics,
      motionDiagnostics,
      comparisons,
      fixtures: reportFixtures,
      fixtureMetrics: fixtureMetricsReport,
      correction,
      coverage: {
        sequences: ["IDLE", "WAVE_HELLO", "POINT_AT"].map((sequence) => ({ sequence, frames: captures.filter((capture) => capture.sequence === sequence && capture.frame).length })),
        fixtureBank: { executed: Boolean(neutralFrame), count: reportFixtures.length },
        artisticReference: Boolean(referencePath),
        aiVision: { available: false, executed: false, note: "Nenhum modelo de visão foi executado; a revisão humana permanece necessária." },
      },
      summary,
    };
    const evidenceManifest = {
      format: "fabuloom.visual-inspection-evidence/0.1",
      generatedAt: report.generatedAt,
      report: "visual-inspection-report.json",
      fullImages: captures.map((capture) => capture.screenshot),
      fixtureRegions: reportFixtures.map((fixture) => ({ id: fixture.id, image: fixture.evidenceImage || null, region: fixture.region, regionSpec: fixture.regionSpec })),
      comparisons: comparisons.map((comparison) => ({ name: comparison.name, diffMask: comparison.diffMask, overlay: comparison.overlay, referenceKind: comparison.referenceKind })),
      geometry: { frameFormat: VISUAL_INSPECTION_FORMAT, captures: "visual-inspection-report.json#captures[].frame" },
      history: { branch: "mission-013-visual-inspector", baseCommit: "e77821b", note: "The capture may include working-tree changes; the final public commit is recorded in the mission handoff." },
      aiVision: { available: false, executed: false, interface: "A future adapter may consume this manifest without changing the deterministic analyzer." },
    };
    await writeFile(path.join(output, "visual-inspection-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    await writeFile(path.join(output, "visual-inspection-report.md"), markdownReport(report), "utf8");
    await writeFile(path.join(output, "visual-inspection-evidence.json"), `${JSON.stringify(evidenceManifest, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ output, status: summary.status, counts: summary.counts, captures: captures.length, fixtures: reportFixtures.length, fixtureMetrics: fixtureMetricsReport, report: path.join(output, "visual-inspection-report.json"), evidence: path.join(output, "visual-inspection-evidence.json") }, null, 2));
    if (summary.status === "needs-correction") process.exitCode = 2;
  } finally {
    server.kill();
  }
}

main().catch((error) => {
  console.error(`[visual-inspector] ${error.stack || error}`);
  process.exitCode = 1;
});
