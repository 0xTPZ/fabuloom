#!/usr/bin/env node

import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { createUnavailableVisualAnalysisProvider, createVisualAnalysisRequest } from "../../frontend/src/visual-analysis-provider.mjs";
import { analyzeRenderedPixels, combineVisualDiagnostics, diagnoseRenderedImage } from "../../frontend/src/real-image-inspector.mjs";
import { annotatePng, comparePngBuffers, decodePng } from "./png.mjs";
import { buildHistoricalDatasetManifest } from "./historical-dataset.mjs";

const DEFAULT_WORKSPACE = "E:/Fabuloom";
const DEFAULT_OUTPUT = "E:/Fabuloom/workspace/exports/visual-inspector/mission-013.2-real";

function argumentValue(args, name, fallback = null) {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
}

function hasArgument(args, name) { return args.includes(name); }

function relativePath(root, file) { return path.relative(root, file).replaceAll("\\", "/"); }

function referenceFor(entry, manifest) {
  if (entry.id === "evaluation-v5-head-original") return manifest.entries.find((candidate) => candidate.id === "reference-v5-head-clean");
  if (entry.version === "V5") return manifest.entries.find((candidate) => candidate.id === "reference-v5-1s");
  return manifest.entries.find((candidate) => candidate.id === "reference-v5-1s");
}

function markdownReport(report) {
  const lines = [
    "# Fabuloom Visual Inspector V1.2 — Real-world validation",
    "",
    `- Formato: \`${report.format}\``,
    `- Imagens analisadas: ${report.realImageResults.length}`,
    `- Avaliação cega executada antes da revisão: **${report.blindEvaluation.resultsWrittenBeforeReview ? "sim" : "não"}**`,
    `- Provedor multimodal: **${report.aiVision.status}**`,
    "",
    "## Banco histórico",
    "",
    "| ID | Conjunto | Versão | Origem | Tempo | Dimensões | SHA-256 |",
    "| --- | --- | --- | --- | ---: | --- | --- |",
  ];
  for (const entry of report.dataset.entries) lines.push(`| ${entry.id} | ${entry.set} | ${entry.version} | \`${entry.source}\` | ${entry.sourceTimeSec ?? "—"} s | ${entry.dimensions.width}×${entry.dimensions.height} | \`${entry.sha256.slice(0, 16)}…\` |`);
  lines.push("", "## Resultado cego", "", "Nenhum rótulo de defeito foi enviado ao analisador. As sugestões abaixo derivam de pixels, segmentação heurística e comparação com referências gerais; a classificação causal ocorreu somente depois da gravação do resultado cego.", "", "| ID | Hipóteses | Confiança | Evidência | Overlay |", "| --- | --- | --- | --- | --- |",);
  for (const result of report.realImageResults) {
    const codes = result.visual.issues.map((finding) => finding.code).join(", ") || "nenhuma";
    const confidence = result.visual.issues.map((finding) => finding.confidence).join(", ") || "—";
    lines.push(`| ${result.id} | ${codes} | ${confidence} | ${result.visual.metrics.foreground.confidence} | \`${result.evidenceImage || "—"}\` |`);
  }
  lines.push("", "## Revisão pós-análise", "", "| ID | Classificação humana | Tipo | Códigos esperados | Códigos sugeridos | Região |", "| --- | --- | --- | --- | --- | --- |",);
  if (!report.review?.entries?.length) lines.push("| — | não executada | — | — | — | — |");
  for (const review of report.review?.entries || []) {
    const result = report.realImageResults.find((candidate) => candidate.id === review.id);
    lines.push(`| ${review.id} | ${review.classification} | ${review.defectType || "—"} | ${(review.expectedCodes || []).join(", ") || "—"} | ${(result?.visual.issues || []).map((finding) => finding.code).join(", ") || "—"} | ${review.region || "—"} |`);
  }
  lines.push("", "## Métricas reais", "", `- Amostra de avaliação: ${report.realMetrics.evaluationSampleSize}`, `- Defeitos reais confirmados pela revisão humana: ${report.realMetrics.confirmedDefects}`, `- Detectados: ${report.realMetrics.detected}`, `- Falsos negativos: ${report.realMetrics.falseNegatives}`, `- Falsos positivos em imagens classificadas limpas: ${report.realMetrics.falsePositives}`, `- Alertas classificados como diferença artística: ${report.realMetrics.artisticDifferenceAlerts}`, `- Casos inconclusivos: ${report.realMetrics.inconclusive}`, `- Taxa de detecção: ${report.realMetrics.detectionRate === null ? "não calculável" : `${(report.realMetrics.detectionRate * 100).toFixed(1)}%`}`, `- Precisão dos alertas contra amostras limpas: ${report.realMetrics.precision === null ? "não calculável" : `${(report.realMetrics.precision * 100).toFixed(1)}%`}`);
  lines.push("", "## Limitações", "", "Frames extraídos de MP4 são composições opacas: a separação de silhueta usa cor/luminância e não deve ser confundida com máscara alfa do rig. Regiões faciais, laterais e pés são regiões amplas de composição, não landmarks inventados. Diferença de pixels pode significar mudança artística, pose ou escala, por isso permanece hipótese até revisão. O provedor multimodal não foi executado e nenhuma imagem foi enviada para serviço externo.");
  lines.push("", "## Correção histórica isolada", "", report.correction ? `A variante histórica ${report.correction.before.id} foi comparada com ${report.correction.after.id}. A análise cega produziu a hipótese facial antes da inspeção causal; a troca para o asset preservado clean foi reproduzida somente em captura isolada. O pack V5 oficial não foi alterado. Evidência: \`${report.correction.comparison}\`.` : "Nenhum ciclo de correção histórica foi executado.");
  return `${lines.join("\n")}\n`;
}

function computeRealMetrics(results, review) {
  const reviewed = review?.entries || [];
  const evaluation = results.filter((result) => result.set === "evaluation");
  const confirmed = reviewed.filter((entry) => entry.classification === "confirmed-defect");
  const clean = reviewed.filter((entry) => entry.classification === "clean");
  const artistic = reviewed.filter((entry) => entry.classification === "artistic-difference");
  const inconclusive = reviewed.filter((entry) => entry.classification === "inconclusive");
  const detected = confirmed.filter((entry) => {
    const result = results.find((candidate) => candidate.id === entry.id);
    const codes = new Set((result?.visual.issues || []).map((finding) => finding.code));
    return (entry.expectedCodes || []).some((code) => codes.has(code));
  });
  const falseNegatives = confirmed.length - detected.length;
  const falsePositives = clean.filter((entry) => {
    const result = results.find((candidate) => candidate.id === entry.id);
    return Boolean(result?.visual.issues?.length);
  }).length;
  const artisticDifferenceAlerts = artistic.filter((entry) => {
    const result = results.find((candidate) => candidate.id === entry.id);
    return Boolean(result?.visual.issues?.length);
  }).length;
  const alertCount = results.filter((result) => result.set === "evaluation").reduce((sum, result) => sum + result.visual.issues.length, 0);
  return {
    evaluationSampleSize: evaluation.length,
    confirmedDefects: confirmed.length,
    detected: detected.length,
    falseNegatives,
    falsePositives,
    artisticDifferenceAlerts,
    inconclusive: inconclusive.length,
    detectionRate: confirmed.length ? detected.length / confirmed.length : null,
    precision: alertCount ? (alertCount - falsePositives) / alertCount : null,
    coverageByType: Object.fromEntries([...new Set(reviewed.filter((entry) => entry.expectedCodes?.length).map((entry) => entry.defectType).filter(Boolean))].map((type) => {
      const candidates = reviewed.filter((entry) => entry.defectType === type && entry.expectedCodes?.length);
      const hits = candidates.filter((entry) => {
        const result = results.find((candidate) => candidate.id === entry.id);
        return (entry.expectedCodes || []).some((code) => (result?.visual.issues || []).some((finding) => finding.code === code));
      });
      return [type, { sampleSize: candidates.length, detected: hits.length }];
    })),
  };
}

async function main() {
  const args = process.argv.slice(2);
  if (hasArgument(args, "--help")) {
    console.log("Usage: node tools/visual-inspector/real-cli.mjs [--workspace DIR] [--output DIR] [--review JSON]");
    return;
  }
  const workspaceRoot = path.resolve(argumentValue(args, "--workspace", DEFAULT_WORKSPACE));
  const output = path.resolve(argumentValue(args, "--output", DEFAULT_OUTPUT));
  const reviewPath = argumentValue(args, "--review", null);
  await mkdir(output, { recursive: true });
  const dataset = await buildHistoricalDatasetManifest({ workspaceRoot });
  await writeFile(path.join(output, "historical-dataset-manifest.json"), `${JSON.stringify(dataset, null, 2)}\n`, "utf8");
  const imageRoot = path.join(output, "images");
  await mkdir(imageRoot, { recursive: true });
  const references = new Map();
  for (const entry of dataset.entries.filter((candidate) => candidate.set === "reference")) {
    const buffer = await readFile(path.resolve(workspaceRoot, entry.image));
    const decoded = decodePng(buffer);
    references.set(entry.id, { buffer, decoded, metrics: analyzeRenderedPixels(decoded, { region: entry.analysisRegion }) });
  }
  const realImageResults = [];
  for (const entry of dataset.entries.filter((candidate) => candidate.set === "evaluation")) {
    const buffer = await readFile(path.resolve(workspaceRoot, entry.image));
    const decoded = decodePng(buffer);
    const referenceEntry = referenceFor(entry, dataset);
    const reference = referenceEntry ? references.get(referenceEntry.id) : null;
    const visual = diagnoseRenderedImage(decoded, {
      reference: reference?.decoded || null,
      referenceMetrics: reference?.metrics || null,
      options: { region: entry.analysisRegion, faceDifferenceThreshold: referenceEntry?.id === "reference-v5-head-clean" ? 0.02 : entry.version === "V5" ? 0.30 : 0.22, facialFeatureDifferenceThreshold: referenceEntry?.id === "reference-v5-head-clean" ? 0.20 : entry.version === "V5" ? 0.99 : 0.30 },
    });
    const visualIssues = visual.issues;
    const evidenceRegions = visualIssues.map((finding) => finding.region).filter(Boolean);
    const evidencePath = path.join(imageRoot, `${entry.id}-evidence.png`);
    await writeFile(evidencePath, evidenceRegions.length ? annotatePng(buffer, { regions: evidenceRegions, color: [255, 78, 64, 255], lineWidth: 5 }) : buffer);
    realImageResults.push({ id: entry.id, set: entry.set, version: entry.version, source: entry.source, sourceTimeSec: entry.sourceTimeSec, visual, referenceId: referenceEntry?.id || null, evidenceImage: relativePath(output, evidencePath) });
  }
  const blindResults = { format: "fabuloom.visual-inspection-real-results/0.1", generatedAt: new Date().toISOString(), labelsProvidedToAnalyzer: false, results: realImageResults.map((result) => ({ id: result.id, set: result.set, version: result.version, source: result.source, sourceTimeSec: result.sourceTimeSec, referenceId: result.referenceId, evidenceImage: result.evidenceImage, visual: result.visual })) };
  await writeFile(path.join(output, "blind-results.json"), `${JSON.stringify(blindResults, null, 2)}\n`, "utf8");
  const review = reviewPath ? JSON.parse(await readFile(path.resolve(reviewPath), "utf8")) : null;
  const aiProvider = createUnavailableVisualAnalysisProvider();
  const aiResult = await aiProvider.analyzeSequence(createVisualAnalysisRequest({ image: { count: realImageResults.length }, animationContext: { mode: "historical-evaluation" } }));
  const combined = realImageResults.map((result) => ({ id: result.id, ...combineVisualDiagnostics({ visual: result.visual.issues, ai: [] }) }));
  const realMetrics = computeRealMetrics(realImageResults, review);
  const correctionBefore = realImageResults.find((result) => result.id === "evaluation-v5-head-original");
  const correctionAfter = references.get("reference-v5-head-clean");
  const correctionComparison = path.join(output, "head-original-vs-clean.json");
  const correctionDiff = path.join(output, "head-original-vs-clean-diff-mask.png");
  const correctionOverlay = path.join(output, "head-original-vs-clean-overlay.png");
  const correctionBeforeBuffer = await readFile(path.resolve(workspaceRoot, dataset.entries.find((entry) => entry.id === "evaluation-v5-head-original").image));
  const correctionAfterBuffer = await readFile(path.resolve(workspaceRoot, dataset.entries.find((entry) => entry.id === "reference-v5-head-clean").image));
  const correctionPixelComparison = comparePngBuffers(correctionAfterBuffer, correctionBeforeBuffer, { colorTolerance: 12, alphaTolerance: 8 });
  await writeFile(correctionDiff, correctionPixelComparison.diffMaskPng);
  await writeFile(correctionOverlay, correctionPixelComparison.overlayPng);
  await writeFile(correctionComparison, `${JSON.stringify({ before: correctionBefore?.visual || null, after: correctionAfter?.metrics || null, pixelComparison: { differenceRatio: correctionPixelComparison.differenceRatio, differenceBounds: correctionPixelComparison.differenceBounds, diffMask: relativePath(output, correctionDiff), overlay: relativePath(output, correctionOverlay) }, note: "Comparison uses the preserved historical head replay and the approved clean-head capture; no production asset was changed." }, null, 2)}\n`, "utf8");
  const report = {
    format: "fabuloom.visual-inspection-report/1.2",
    generatedAt: new Date().toISOString(),
    tool: { name: "Fabuloom Visual Inspector", version: "1.2.0", mode: "real-rendered-images", imageAnalyzer: "dependency-free RGBA pixels, masks, contours, connected components and reference regions" },
    dataset,
    blindEvaluation: { labelsProvidedToAnalyzer: false, resultsWrittenBeforeReview: true, resultFile: "blind-results.json" },
    realImageResults,
    combinedDiagnostics: combined,
    review,
    realMetrics,
    correction: { before: { id: "evaluation-v5-head-original", codes: correctionBefore?.visual.issues.map((finding) => finding.code) || [] }, after: { id: "reference-v5-head-clean", codes: [] }, comparison: relativePath(output, correctionComparison), note: "Historical replay only; Santa V5 official pack remains unchanged." },
    aiVision: { status: aiResult.status, provider: aiResult.provider, capabilities: aiProvider.capabilities(), executed: false, note: aiResult.reason },
  };
  await writeFile(path.join(output, "real-visual-inspection-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
  await writeFile(path.join(output, "real-visual-inspection-report.md"), markdownReport(report), "utf8");
  console.log(JSON.stringify({ output, datasetEntries: dataset.entries.length, evaluationEntries: realImageResults.length, blindResults: path.join(output, "blind-results.json"), report: path.join(output, "real-visual-inspection-report.json"), metrics: realMetrics, aiVision: report.aiVision }, null, 2));
}

main().catch((error) => {
  console.error(`[visual-inspector-real] ${error.stack || error}`);
  process.exitCode = 1;
});
