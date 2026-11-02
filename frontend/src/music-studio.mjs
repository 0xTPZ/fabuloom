import { drawLivingWorldFrame, MUSIC_STUDIO_STYLE_PALETTES, shortRange, validateMusicStudioProject } from "./music-studio-renderer.mjs";

export { shortRange, validateMusicStudioProject } from "./music-studio-renderer.mjs";

const $ = (selector) => document.querySelector(selector);
const formatTime = (ms) => `${Math.floor(Math.max(0, Number(ms) || 0) / 60000)}:${String(Math.floor((Math.max(0, Number(ms) || 0) % 60000) / 1000)).padStart(2, "0")}`;
const formatSeconds = (ms) => `${(Math.max(0, Number(ms) || 0) / 1000).toFixed(1)} s`;

const state = { catalog: [], analysis: null, project: null, images: {}, animation: null, selectedAsset: "" };

async function apiJSON(url, options) {
  const response = await fetch(url, { cache: "no-store", ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function setStatus(message, error = false) {
  const node = $("#music-status");
  if (node) { node.textContent = message; node.classList.toggle("is-error", error); }
}

function drawWaveform() {
  const canvas = $("#music-waveform");
  const values = state.analysis?.waveform?.values || [];
  if (!canvas) return;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#0a1425"; context.fillRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = "rgba(120,169,255,.15)"; context.beginPath(); context.moveTo(0, canvas.height / 2); context.lineTo(canvas.width, canvas.height / 2); context.stroke();
  if (!values.length) return;
  const barWidth = canvas.width / values.length;
  values.forEach((value, index) => { const height = Math.max(2, value * canvas.height * .82); const gradient = context.createLinearGradient(0, (canvas.height - height) / 2, 0, (canvas.height + height) / 2); gradient.addColorStop(0, "#a987ff"); gradient.addColorStop(1, "#4f8bdb"); context.fillStyle = gradient; context.fillRect(index * barWidth, (canvas.height - height) / 2, Math.max(1, barWidth - 1), height); });
}

function updateRangeReadout() {
  const start = Number($("#music-short-start")?.value || 0) * 1000;
  const end = Number($("#music-short-end")?.value || 0) * 1000;
  const node = $("#music-short-duration");
  if (node) node.textContent = formatSeconds(Math.max(0, end - start));
}

function setRange(startMs, endMs) {
  const duration = Number(state.analysis?.metadata?.duration_ms || 0);
  if (!duration) return;
  const start = Math.max(0, Math.min(duration - 15000, Number(startMs) || 0));
  const end = Math.min(duration, Math.max(start + 15000, Math.min(start + 30000, Number(endMs) || start + 24000)));
  $("#music-short-start").value = (start / 1000).toFixed(1);
  $("#music-short-end").value = (end / 1000).toFixed(1);
  updateRangeReadout();
}

function renderCandidates() {
  const container = $("#music-candidates");
  container.replaceChildren();
  const candidates = state.analysis?.energy_candidates || [];
  if (!candidates.length) { container.textContent = "Nenhuma janela RMS encontrada."; return; }
  candidates.forEach((candidate, index) => {
    const button = document.createElement("button"); button.type = "button"; button.className = "music-candidate"; button.innerHTML = `<strong>${index + 1} · ${formatTime(candidate.start_ms)}–${formatTime(candidate.end_ms)}</strong><small>RMS médio ${(candidate.mean_rms * 100).toFixed(1)}% · janela heurística</small>`;
    button.addEventListener("click", () => setRange(candidate.start_ms, candidate.start_ms + 24000)); container.appendChild(button);
  });
}

function catalogOption(asset) {
  const option = document.createElement("option"); option.value = asset.asset; option.textContent = `${asset.filename} · ${formatTime(asset.duration_ms || 0)}`; return option;
}

async function analyzeSelected() {
  const select = $("#music-source-select"); state.selectedAsset = select.value;
  if (!state.selectedAsset) return;
  setStatus("Decodificando a faixa local com FFmpeg…");
  try {
    state.analysis = await apiJSON(`/api/music/analyze?asset=${encodeURIComponent(state.selectedAsset)}`);
    const metadata = state.analysis.metadata;
    $("#music-source-duration").textContent = `Duração: ${formatSeconds(metadata.duration_ms)}`;
    $("#music-source-format").textContent = `Formato: ${metadata.format_name || "—"} · ${metadata.sample_rate || "—"} Hz · ${metadata.channels || "—"} canais`;
    $("#music-source-status").textContent = "Análise real concluída";
    drawWaveform(); renderCandidates();
    const selected = state.analysis.selected_candidate || state.analysis.energy_candidates?.reduce((best, item) => !best || item.mean_rms > best.mean_rms ? item : best, null);
    setRange(selected?.start_ms || 0, (selected?.start_ms || 0) + 24000);
    setStatus("Faixa pronta. Salve o projeto para preparar os assets ambientais.");
    drawPreview();
  } catch (error) { state.analysis = null; drawWaveform(); renderCandidates(); setStatus(`Falha na análise: ${error.message}`, true); }
}

function previewProject() {
  if (state.project) return state.project;
  if (!state.analysis) return null;
  const palette = MUSIC_STUDIO_STYLE_PALETTES[$("#music-style-select")?.value] || MUSIC_STUDIO_STYLE_PALETTES["topazioverse-living-worlds"];
  const duration = state.analysis.metadata.duration_ms;
  return { format: "fabuloom.music-studio-project/0.1", id: "preview", source: { filename: state.analysis.source.filename, analysis: state.analysis.metadata }, style: { id: $("#music-style-select").value, palette }, visual_policy: { narrator: null, lip_sync: false, characters: [] }, analysis: { waveform: state.analysis.waveform }, full: { width: 1920, height: 1080, fps: 30, duration_ms: duration, scenes: Array.from({ length: 6 }, (_, index) => ({ id: `preview-${index}`, asset_id: `none-${index}`, start_ms: Math.round(index * duration / 6), end_ms: Math.round((index + 1) * duration / 6), camera: { zoom: 1, pan_x: 0, pan_y: 0 } })) }, short: { width: 1080, height: 1920, fps: 30, duration_ms: 24000, scenes: [{ id: "preview-short", asset_id: "none", start_ms: 0, end_ms: 24000, camera: {} }] }, short_selection: { start_ms: 0, end_ms: 24000 }, assets: [] };
}

function drawPreview() {
  const canvas = $("#music-preview"); const project = previewProject();
  if (!canvas || !project) return;
  const context = canvas.getContext("2d"); const timeMs = state.project?.full?.duration_ms ? (performance.now() % state.project.full.duration_ms) : (performance.now() % Math.max(1, project.full.duration_ms));
  drawLivingWorldFrame(context, project, state.images, timeMs, "full");
  const scene = project.full.scenes.find((item) => timeMs >= item.start_ms && timeMs < item.end_ms) || project.full.scenes[0];
  $("#music-preview-scene").textContent = state.project ? (state.project.assets.find((item) => item.id === scene.asset_id)?.label || "Ambiente sem personagens") : "Prévia de estilo · salve para carregar cenas";
  $("#music-preview-time").textContent = formatTime(timeMs);
  if (state.animation === null) state.animation = requestAnimationFrame(function loop() { state.animation = requestAnimationFrame(loop); drawPreview(); });
}

async function loadImages(project) {
  state.images = {};
  for (const asset of project.assets || []) {
    const image = new Image(); image.src = `/exports/${project.asset_root.split("/").map(encodeURIComponent).join("/")}/${asset.path.split("/").map(encodeURIComponent).join("/")}`;
    await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = () => reject(new Error(`asset visual indisponível: ${asset.path}`)); });
    state.images[asset.id] = image;
  }
}

function projectFieldsFrom(project) {
  state.project = validateMusicStudioProject(project);
  state.selectedAsset = project.source.workspace_relative.replace(/^workspace\/inputs\/music\//, "");
  $("#music-project-name").value = project.id.replace(/^music-studio-v1-/, "");
  $("#music-style-select").value = project.style.id;
  $("#music-short-start").value = (project.short_selection.start_ms / 1000).toFixed(1);
  $("#music-short-end").value = (project.short_selection.end_ms / 1000).toFixed(1);
  $("#music-project-state").textContent = "salvo localmente";
  state.analysis = { source: project.source, metadata: project.source.analysis, waveform: project.analysis.waveform, energy_candidates: project.analysis.energy_candidates };
  $("#music-source-duration").textContent = `Duração: ${formatSeconds(project.source.analysis.duration_ms)}`;
  $("#music-source-format").textContent = `Formato: ${project.source.analysis.format_name || "—"} · ${project.source.analysis.sample_rate || "—"} Hz · ${project.source.analysis.channels || "—"} canais`;
  $("#music-source-status").textContent = "Projeto reaberto";
  $("#music-source-select").value = project.source.workspace_relative.replace(/^workspace\/inputs\/music\//, "");
  drawWaveform(); renderCandidates(); updateRangeReadout(); void loadImages(project).then(drawPreview).catch((error) => setStatus(error.message, true));
}

async function refreshProjects() {
  const select = $("#music-project-select");
  const data = await apiJSON("/api/music/projects"); select.replaceChildren(new Option("Projetos locais…", ""));
  data.projects.forEach((project) => select.appendChild(new Option(`${project.title} · ${project.source}`, project.id)));
}

async function saveProject() {
  if (!state.analysis || !state.selectedAsset) { setStatus("Analise uma faixa antes de salvar o projeto.", true); return; }
  const range = shortRange(Number($("#music-short-start").value) * 1000, Number($("#music-short-end").value) * 1000, state.analysis.metadata.duration_ms);
  setStatus("Preparando projeto e copiando somente assets ambientais…");
  try {
    const response = await apiJSON("/api/music/project", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset: state.selectedAsset, style_id: $("#music-style-select").value, name: $("#music-project-name").value, short_start_ms: range.start_ms, short_end_ms: range.end_ms }) });
    projectFieldsFrom(response.project); await refreshProjects(); $("#music-project-select").value = response.project.id; setStatus("Projeto salvo localmente. As duas timelines permanecem independentes.");
  } catch (error) { setStatus(`Falha ao salvar projeto: ${error.message}`, true); }
}

async function pollJob(jobId) {
  const progress = $("#music-export-progress"); const bar = $("#music-progress-bar"); const label = $("#music-progress-label"); progress.hidden = false;
  for (;;) {
    const job = await apiJSON(`/api/music/jobs/${jobId}`); const value = Number(job.progress?.progress || 0); bar.style.width = `${value}%`; label.textContent = `${job.progress?.stage || job.state} · ${value}%`;
    if (job.state === "completed") { const root = `/exports/${String(job.project || "").replace(/\/project\.json$/, "")}`; const report = await apiJSON(`${root}/reports/technical-report.json`); const links = $("#music-export-links"); links.replaceChildren(); Object.entries(report.outputs || {}).forEach(([mode, output]) => { const anchor = document.createElement("a"); anchor.href = `/exports/${output.video}`; anchor.target = "_blank"; anchor.rel = "noreferrer"; anchor.textContent = `Abrir MP4 ${mode === "full" ? "16:9" : "9:16"} ↗`; links.appendChild(anchor); }); setStatus("Exportação concluída. Links exibem apenas os formatos realmente gerados."); return; }
    if (job.state === "failed") throw new Error(`exportação falhou; log local: ${job.log || "indisponível"}`);
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
}

async function exportFormats(formats) {
  if (!state.project) { setStatus("Salve ou reabra um projeto antes de exportar.", true); return; }
  setStatus(`Exportando ${formats === "both" ? "vídeo completo e Short" : formats}…`);
  try { const result = await apiJSON("/api/music/export", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: state.project.id, formats }) }); await pollJob(result.job_id); }
  catch (error) { setStatus(`Falha na exportação: ${error.message}`, true); }
}

export async function initMusicStudio() {
  const source = $("#music-source-select"); if (!source) return;
  $("#music-refresh")?.addEventListener("click", () => void loadCatalog());
  source.addEventListener("change", () => void analyzeSelected());
  ["#music-short-start", "#music-short-end"].forEach((selector) => $(selector)?.addEventListener("input", updateRangeReadout));
  $("#music-save")?.addEventListener("click", () => void saveProject());
  $("#music-style-select")?.addEventListener("change", () => drawPreview());
  $("#music-export-full")?.addEventListener("click", () => void exportFormats("full"));
  $("#music-export-short")?.addEventListener("click", () => void exportFormats("short"));
  $("#music-export-both")?.addEventListener("click", () => void exportFormats("both"));
  $("#music-project-select")?.addEventListener("change", async (event) => { if (!event.target.value) return; try { projectFieldsFrom(await apiJSON(`/api/music/project?id=${encodeURIComponent(event.target.value)}`)); setStatus("Projeto reaberto a partir do workspace local."); } catch (error) { setStatus(`Falha ao reabrir: ${error.message}`, true); } });
  await loadCatalog();
  await refreshProjects();
}

async function loadCatalog() {
  try {
    const data = await apiJSON("/api/music/catalog"); state.catalog = data.assets || []; const select = $("#music-source-select"); const previous = state.selectedAsset; select.replaceChildren(); state.catalog.forEach((asset) => select.appendChild(catalogOption(asset))); const preferred = state.catalog.find((asset) => /O Chamado do Vazio/i.test(asset.filename)) || state.catalog[0]; select.value = previous && state.catalog.some((asset) => asset.asset === previous) ? previous : preferred?.asset || ""; await analyzeSelected();
  } catch (error) { setStatus(`Biblioteca de música indisponível: ${error.message}`, true); }
}

