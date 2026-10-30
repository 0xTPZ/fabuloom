import path from "node:path";

export const VISUAL_QA_REPORT_FORMAT = "fabuloom.visual-qa-gate/0.1";
export const VISUAL_QA_EVIDENCE_FORMAT = "fabuloom.visual-qa-evidence/0.1";

function resolved(value) { return path.resolve(String(value)); }

/** Keep evidence and generated artifacts inside the approved Fabuloom workspace. */
export function assertWorkspacePath(candidate, workspaceRoot = "E:/Fabuloom") {
  const root = resolved(workspaceRoot);
  const target = resolved(candidate);
  try {
    target.replace(root, "");
    path.relative(root, target);
    if (target !== root && !target.startsWith(`${root}${path.sep}`)) throw new Error(`path outside workspace: ${candidate}`);
  } catch {
    throw new Error(`path outside workspace: ${candidate}`);
  }
  return target;
}

export function relativeWorkspacePath(candidate, workspaceRoot = "E:/Fabuloom") {
  const target = assertWorkspacePath(candidate, workspaceRoot);
  return path.relative(resolved(workspaceRoot), target).replaceAll("\\", "/");
}

export function exportUrl(candidate, exportRoot = "E:/Fabuloom/workspace/exports") {
  const root = resolved(exportRoot);
  const target = assertWorkspacePath(candidate);
  if (target !== root && !target.startsWith(`${root}${path.sep}`)) throw new Error(`evidence is not under exports: ${candidate}`);
  return `/exports/${path.relative(root, target).replaceAll("\\", "/")}`;
}

function issuesFromReport(report) {
  return [
    ...(report?.frameDiagnostics || []).flatMap((entry) => entry.issues || []),
    ...(report?.motionDiagnostics || []).flatMap((entry) => entry.issues || []),
  ];
}

export function technicalGateStatus(executions = []) {
  const captureFailures = executions.flatMap((execution) => execution.report?.captures?.filter((capture) => capture.error).map((capture) => `${execution.id}:${capture.name}`) || []);
  const errors = executions.flatMap((execution) => issuesFromReport(execution.report).filter((finding) => finding.severity === "error").map((finding) => ({ execution: execution.id, ...finding })));
  const hypotheses = executions.flatMap((execution) => issuesFromReport(execution.report).filter((finding) => finding.severity === "hypothesis").map((finding) => ({ execution: execution.id, ...finding })));
  const processFailures = executions.filter((execution) => execution.exitCode !== 0);
  const status = processFailures.length || captureFailures.length || errors.length ? "failed" : "passed";
  return { status, reviewRequired: hypotheses.length > 0, processFailures: processFailures.map((execution) => execution.id), captureFailures, errors, hypotheses };
}

export function validateEvidencePackage(evidence, workspaceRoot = "E:/Fabuloom") {
  if (!evidence || evidence.format !== VISUAL_QA_EVIDENCE_FORMAT) throw new TypeError("invalid visual QA evidence format");
  const paths = [];
  for (const item of evidence.images || []) paths.push(item.path);
  for (const item of evidence.comparisons || []) paths.push(item.diffMaskPath, item.overlayPath);
  for (const item of paths.filter(Boolean)) assertWorkspacePath(item, workspaceRoot);
  return true;
}

export function buildEvidencePackage({ generatedAt, plan, executions, comparisons = [], correction = null }) {
  const images = executions.flatMap((execution) => (execution.report?.captures || []).filter((capture) => capture.screenshot).map((capture) => ({
    execution: execution.id,
    name: capture.name,
    reason: capture.reason || null,
    path: path.resolve(execution.output, capture.screenshot),
    url: exportUrl(path.resolve(execution.output, capture.screenshot)),
  })));
  const comparisonEvidence = comparisons.map((comparison) => ({
    name: comparison.name,
    purpose: comparison.purpose,
    beforePath: comparison.beforePath,
    afterPath: comparison.afterPath,
    beforeUrl: comparison.beforeUrl || (comparison.beforePath ? exportUrl(comparison.beforePath) : null),
    afterUrl: comparison.afterUrl || (comparison.afterPath ? exportUrl(comparison.afterPath) : null),
    diffMaskPath: comparison.diffMaskPath,
    overlayPath: comparison.overlayPath,
    diffMaskUrl: comparison.diffMaskPath ? exportUrl(comparison.diffMaskPath) : null,
    overlayUrl: comparison.overlayPath ? exportUrl(comparison.overlayPath) : null,
    differenceRatio: comparison.differenceRatio,
    bounds: comparison.differenceBounds || null,
  }));
  return {
    format: VISUAL_QA_EVIDENCE_FORMAT,
    generatedAt,
    plan: { format: plan.format, captures: plan.captures.map(({ name, mode, timeMs, sequence, reason }) => ({ name, mode, timeMs, sequence: sequence || null, reason: reason || null })) },
    images,
    comparisons: comparisonEvidence,
    executions: executions.map((execution) => ({ id: execution.id, variant: execution.variant, reportPath: execution.reportPath, exitCode: execution.exitCode, status: execution.status })),
    correction,
    review: { technical: "automated", artistic: "pending-human-review", multimodal: "not-executed" },
  };
}

export function markdownQaReport(report) {
  const lines = [
    "# Fabuloom Visual QA Gate",
    "",
    `- Formato: \`${report.format}\``,
    `- Status técnico: **${report.technicalGate.status}**`,
    `- Revisão artística: **${report.artisticReview.status}**`,
    `- Provedor multimodal: **${report.multimodal.status}**`,
    "",
    "A aprovação artística continua humana. O gate automatizado comprova a execução, a integridade dos quadros e as evidências determinísticas; ele não declara que a arte é final.",
    "",
    "## Plano de captura",
    "",
    "| Captura | Tempo | Modo | Motivo |",
    "| --- | ---: | --- | --- |",
    ...report.plan.captures.map((capture) => `| ${capture.name} | ${capture.timeMs} ms | ${capture.mode} | ${capture.reason || "—"} |`),
    "",
    "## Execuções",
    "",
    "| Execução | Variante | Status | Saída |",
    "| --- | --- | --- | --- |",
    ...report.executions.map((execution) => `| ${execution.id} | ${execution.variant} | ${execution.status} | \`${execution.reportPath}\` |`),
    "",
    "## Ciclo de correção assistida",
    "",
    report.correction ? `- Escopo: **${report.correction.scope}**\n- Status: **${report.correction.status}**\n- Tentativas: ${report.correction.attempts}/${report.correction.maxAttempts}\n- Antes: ${report.correction.beforeVariant}; depois: ${report.correction.afterVariant}\n- A alteração foi isolada e os assets oficiais não foram modificados.` : "Nenhum ciclo de correção foi executado.",
    "",
    "## Evidências",
    "",
    ...report.evidencePackage.comparisons.map((comparison) => `- ${comparison.name}: diferença ${(Number(comparison.differenceRatio || 0) * 100).toFixed(2)}%; máscara \`${comparison.diffMaskPath || "—"}\`; overlay \`${comparison.overlayPath || "—"}\`.`),
    "",
    "## Limitações",
    "",
    ...report.limitations.map((limitation) => `- ${limitation}`),
    "",
  ];
  return `${lines.join("\n")}\n`;
}
