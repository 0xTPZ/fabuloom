#!/usr/bin/env node

import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { SANTA_V5_POINT_AT_CLIP, SANTA_V5_WAVE_HELLO_CLIP } from "../../frontend/src/santa-v5-engine.ts";
import { analyzeRenderedPixels, diagnoseRenderedImage } from "../../frontend/src/real-image-inspector.mjs";
import { createUnavailableVisualAnalysisProvider } from "../../frontend/src/visual-analysis-provider.mjs";
import { executeCorrectionAttempt, createCorrectionAttempt } from "./assisted-correction.mjs";
import { buildSantaV5QaPlan } from "./qa-plan.mjs";
import { comparePngBuffers, decodePng } from "./png.mjs";
import {
  VISUAL_QA_REPORT_FORMAT,
  assertWorkspacePath,
  buildEvidencePackage,
  exportUrl,
  markdownQaReport,
  technicalGateStatus,
  validateEvidencePackage,
} from "./qa-report.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const studioRoot = path.resolve(scriptDirectory, "..", "..");
const workspaceRoot = path.resolve("E:/Fabuloom");
const defaultOutput = path.resolve("E:/Fabuloom/workspace/exports/visual-qa/mission-013.3");

function arg(args, name, fallback = null) {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { ...options, windowsHide: true });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr?.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", reject);
    child.on("close", (code, signal) => resolve({ code, signal, stdout, stderr }));
  });
}

async function runInspector({ id, variant, output, planPath, port }) {
  await mkdir(output, { recursive: true });
  const cliPath = path.join(studioRoot, "tools", "visual-inspector", "cli.mjs");
  const result = await run(process.execPath, [cliPath, "--output", output, "--variant", variant, "--plan", planPath, "--port", String(port)], { cwd: studioRoot });
  await writeFile(path.join(output, "cli.stdout.log"), result.stdout, "utf8");
  await writeFile(path.join(output, "cli.stderr.log"), result.stderr, "utf8");
  const reportPath = path.join(output, "visual-inspection-report.json");
  let report = null;
  if (existsSync(reportPath)) report = JSON.parse(await readFile(reportPath, "utf8"));
  return {
    id,
    variant,
    output,
    report,
    reportPath,
    reportUrl: exportUrl(reportPath),
    exitCode: result.code,
    status: result.code === 0 ? "completed" : "failed",
    stdoutPath: path.join(output, "cli.stdout.log"),
    stderrPath: path.join(output, "cli.stderr.log"),
  };
}

async function loadPng(file) {
  return decodePng(await readFile(file));
}

function relativeToOutput(output, file) {
  return path.relative(output, file).replaceAll("\\", "/");
}

function comparisonEvidence({ output, name, purpose, beforePath, afterPath }) {
  return readFile(beforePath).then(async (beforeBuffer) => {
    const afterBuffer = await readFile(afterPath);
    const comparison = comparePngBuffers(beforeBuffer, afterBuffer, { colorTolerance: 12, alphaTolerance: 8 });
    const diffMaskPath = path.join(output, "comparisons", `${name}-diff-mask.png`);
    const overlayPath = path.join(output, "comparisons", `${name}-overlay.png`);
    if (comparison.compatible) {
      await writeFile(diffMaskPath, comparison.diffMaskPng);
      await writeFile(overlayPath, comparison.overlayPng);
    }
    return {
      name,
      purpose,
      beforePath,
      afterPath,
      diffMaskPath: comparison.compatible ? diffMaskPath : null,
      overlayPath: comparison.compatible ? overlayPath : null,
      differenceRatio: comparison.differenceRatio,
      meanChannelDifference: comparison.meanChannelDifference || null,
      differenceBounds: comparison.differenceBounds || null,
      compatible: comparison.compatible,
      reason: comparison.reason || null,
      beforeUrl: exportUrl(beforePath),
      afterUrl: exportUrl(afterPath),
    };
  });
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes("--help")) {
    console.log("Usage: node tools/visual-inspector/qa-gate.mjs [--output DIR] [--port PORT] [--variant production-v5] [--correction] [--max-attempts N]");
    return;
  }
  const output = assertWorkspacePath(arg(args, "--output", defaultOutput), workspaceRoot);
  const port = Number(arg(args, "--port", "8813"));
  const maxAttempts = Number(arg(args, "--max-attempts", "1"));
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new RangeError("port must be an integer between 1024 and 65535");
  if (!Number.isInteger(maxAttempts) || maxAttempts < 1) throw new RangeError("max-attempts must be a positive integer");
  await mkdir(output, { recursive: true });
  await mkdir(path.join(output, "comparisons"), { recursive: true });

  const plan = buildSantaV5QaPlan({ waveClip: SANTA_V5_WAVE_HELLO_CLIP, pointClip: SANTA_V5_POINT_AT_CLIP });
  const planPath = path.join(output, "qa-plan.json");
  await writeFile(planPath, `${JSON.stringify(plan, null, 2)}\n`, "utf8");

  const requestedCorrection = args.includes("--correction");
  const executions = [];
  if (requestedCorrection) {
    executions.push(await runInspector({ id: "historical-before", variant: "historical-head-original", output: path.join(output, "before-historical-head-original"), planPath, port }));
    executions.push(await runInspector({ id: "production-after", variant: "production-v5", output: path.join(output, "after-production-v5"), planPath, port: port + 1 }));
  } else {
    executions.push(await runInspector({ id: "production", variant: arg(args, "--variant", "production-v5"), output: path.join(output, "production"), planPath, port }));
  }

  const comparisons = [];
  let pixelDiagnosis = null;
  if (requestedCorrection) {
    const beforeNeutral = path.join(executions[0].output, "neutral.png");
    const afterNeutral = path.join(executions[1].output, "neutral.png");
    const comparison = await comparisonEvidence({ output, name: "historical-head-original-vs-production-clean", purpose: "historical Santa V5 facial-asset regression replay", beforePath: beforeNeutral, afterPath: afterNeutral });
    comparisons.push(comparison);
    const beforePixels = await loadPng(beforeNeutral);
    const afterPixels = await loadPng(afterNeutral);
    pixelDiagnosis = diagnoseRenderedImage(beforePixels, {
      reference: afterPixels,
      referenceMetrics: analyzeRenderedPixels(afterPixels),
      options: { region: { left: 80, top: 620, right: 680, bottom: 1820 }, faceDifferenceThreshold: 0.02, facialFeatureDifferenceThreshold: 0.20 },
    });
  }

  let correction = null;
  if (requestedCorrection) {
    const state = createCorrectionAttempt({
      id: "santa-v5-historical-head-replay",
      scope: "experimental-historical-replay",
      maxAttempts,
      target: "head.png → head-clean.png selection in isolated capture variant",
      evidence: ["historical-head-original-vs-production-clean"],
    });
    const result = await executeCorrectionAttempt({
      state,
      snapshot: async () => ({ variant: "historical-head-original", officialAssetsChanged: false }),
      apply: async () => ({ variant: "production-v5", officialAssetsChanged: false, sourceMutation: false }),
      validate: async ({ after }) => {
        const afterReport = executions[1].report;
        const afterErrors = (afterReport?.summary?.counts?.error || 0) + (afterReport?.frameDiagnostics || []).flatMap((entry) => entry.issues || []).filter((finding) => finding.severity === "error").length;
        const compatible = comparisons[0]?.compatible === true;
        const facialSignal = pixelDiagnosis?.issues?.some((finding) => ["facial-region-difference", "facial-feature-difference"].includes(finding.code));
        return {
          accepted: after.variant === "production-v5" && afterErrors === 0 && compatible && Boolean(facialSignal),
          reason: facialSignal ? "historical facial difference is visible in the isolated before/after evidence" : "no facial difference signal was produced by the pixel analyzer",
          afterErrors,
          compatible,
          facialSignal: Boolean(facialSignal),
        };
      },
      rollback: async () => undefined,
    });
    correction = {
      ...result,
      beforeVariant: "historical-head-original",
      afterVariant: "production-v5",
      maxAttempts,
      beforeReport: executions[0].reportUrl,
      afterReport: executions[1].reportUrl,
      pixelDiagnosis: pixelDiagnosis ? { issueCodes: pixelDiagnosis.issues.map((finding) => finding.code), review: pixelDiagnosis.review, comparison: pixelDiagnosis.comparison } : null,
      note: "A correção é uma reprodução histórica isolada: a variante experimental usa o asset original e a variante de produção usa o pack limpo. Nenhum asset oficial foi sobrescrito.",
    };
  }

  const technicalGate = technicalGateStatus(executions);
  const provider = createUnavailableVisualAnalysisProvider({ reason: "Nenhum VisualAnalysisProvider multimodal está configurado nesta execução offline." });
  const multimodalResult = await provider.analyzeSequence({ format: "fabuloom.visual-analysis-provider/0.1", images: [] });
  const artisticReview = { status: "pending-human-review", approved: false, note: "O gate não substitui a avaliação humana da qualidade artística, anatomia ou naturalidade do movimento." };
  const evidencePackage = buildEvidencePackage({ generatedAt: new Date().toISOString(), plan, executions, comparisons, correction, outputRoot: output });
  validateEvidencePackage(evidencePackage, workspaceRoot);
  const report = {
    format: VISUAL_QA_REPORT_FORMAT,
    generatedAt: evidencePackage.generatedAt,
    tool: { name: "Fabuloom Visual QA Gate", version: "1.0.0", inspector: "Visual Inspector V1.2", renderer: "SantaV5SceneRenderer → LayeredCharacterRenderer", captureBackend: "Microsoft Edge headless over loopback HTTP" },
    character: { id: "topazio-narrator-santa-v5", voiceId: "pm_santa", packFormat: "fabuloom.character/0.1" },
    plan: evidencePackage.plan,
    executions: executions.map((execution) => ({ id: execution.id, variant: execution.variant, status: execution.status, exitCode: execution.exitCode, reportPath: relativeToOutput(output, execution.reportPath), reportUrl: execution.reportUrl, outputUrl: exportUrl(execution.output) })),
    technicalGate,
    artisticReview,
    multimodal: { status: multimodalResult.status, provider: provider.providerMetadata(), capabilities: provider.capabilities(), humanReviewRequired: multimodalResult.humanReviewRequired, reason: multimodalResult.reason },
    correction,
    evidencePackage,
    limitations: [
      "A análise multimodal não foi executada; o provider indisponível retorna not-executed explicitamente.",
      "A análise de pixels e a geometria detectam evidências técnicas, mas não aprovam a arte nem garantem qualidade profissional.",
      "O ciclo accepted é um replay histórico isolado entre variantes preservada e limpa; ele não representa uma alteração destrutiva no pack oficial.",
    ],
  };
  await writeFile(path.join(output, "visual-qa-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
  await writeFile(path.join(output, "visual-qa-evidence.json"), `${JSON.stringify(evidencePackage, null, 2)}\n`, "utf8");
  await writeFile(path.join(output, "visual-qa-report.md"), markdownQaReport(report), "utf8");
  console.log(JSON.stringify({ output, technicalStatus: technicalGate.status, artisticReview: artisticReview.status, correction: correction?.status || "not-requested", captures: plan.captures.length, report: path.join(output, "visual-qa-report.json"), evidence: path.join(output, "visual-qa-evidence.json") }, null, 2));
  if (technicalGate.status === "failed" || (requestedCorrection && correction.status !== "accepted")) process.exitCode = 2;
}

main().catch((error) => {
  console.error(`[visual-qa-gate] ${error.stack || error}`);
  process.exitCode = 1;
});
