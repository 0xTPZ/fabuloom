import { AudioTimelinePlayer } from "./audio.ts";
import {
  NarratorAvatarRenderer,
  NarratorSceneRenderer,
  createOfficialNarratorAvatarPack,
  createNarratorTimeline,
} from "./narrator-mode.mjs";
import { manifestVoiceId, narrationForCharacter, narrationForUrl, TOPAZIO_NARRATION_CATALOG } from "./topazio-narrations.mjs";
import { validateManifest } from "./timeline.ts";
import { resolveCinematicTransform } from "./cinematic-composition.mjs";
import {
  DEV_LINKS,
  OFFICIAL_NARRATORS,
  PRODUCTION_EXPORTS,
  PRODUCTION_PROFILES,
  STUDIO_SECTIONS,
  officialNarratorById,
  sectionById,
} from "./studio-config.mjs";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const previewCanvas = $("#studio-preview");
const sceneImage = new Image();
sceneImage.src = "/assets/narrator-mode/topazio-storyteller-office.svg";

let activeRoute = "dashboard";
let player = null;
let manifest = null;
let sceneRenderer = null;
let avatarRenderer = null;
let selectedNarration = narrationForCharacter("santa");
let activeNarrator = officialNarratorById("santa");
let loadToken = 0;
let currentProject = null;
let selectedSceneId = null;
let exportInProgress = false;
let previewMode = "cinematic";
let voiceVerified = false;
const cinematicImages = new Map();

async function api(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function projectApiPath(suffix = "") {
  return currentProject ? `/api/projects/${encodeURIComponent(currentProject.id)}${suffix}` : null;
}

function renderProjectExports() {
  const list = $("#project-export-list");
  if (!list) return;
  list.replaceChildren();
  (currentProject?.exports || []).forEach((item) => {
    const row = document.createElement("div"); row.className = "export-row";
    const relative = item.path.split("\\").join("/");
    row.innerHTML = `<span><strong>Projeto atual · MP4</strong><small>${item.format} · ${item.created_at}</small></span><a href="/exports/${relative.replace(/^workspace[\\/]exports[\\/]/, "")}" target="_blank" rel="noreferrer">Abrir arquivo ↗</a>`;
    list.appendChild(row);
  });
}

function renderProjectScenes() {
  const list = $("#scene-list"); if (!list) return;
  list.replaceChildren();
  if (currentProject?.scenes?.length && !currentProject.scenes.some((scene) => scene.id === selectedSceneId)) selectedSceneId = currentProject.scenes[0].id;
  (currentProject?.scenes || []).forEach((scene, index) => {
    const row = document.createElement("div"); row.className = "scene-editor-row"; row.classList.toggle("is-selected", scene.id === selectedSceneId);
    const number = document.createElement("strong"); number.textContent = String(index + 1).padStart(2, "0");
    const copy = document.createElement("div"); const title = document.createElement("strong"); title.textContent = scene.title || `Cena ${index + 1}`;
    const text = document.createElement("small"); text.textContent = `${scene.text} · ${formatTime(scene.duration_ms || 0)}`; copy.append(title, text);
    const controls = document.createElement("div");
    if (scene.image) { const image = document.createElement("img"); image.src = projectApiPath(`/asset/${encodeURIComponent(scene.image)}`); image.alt = "Imagem da cena"; controls.appendChild(image); }
    const input = document.createElement("input"); input.type = "file"; input.accept = "image/png,image/jpeg,image/webp";
    input.addEventListener("change", () => { if (input.files[0]) void uploadAsset(input.files[0], "image", scene.id); }); controls.appendChild(input);
    row.addEventListener("click", (event) => { if (event.target?.tagName !== "INPUT") { selectedSceneId = scene.id; renderProjectScenes(); } });
    row.append(number, copy, controls); list.appendChild(row);
  });
  if (!currentProject?.scenes?.length) list.innerHTML = '<div class="loading-row">Salve um roteiro para criar a primeira cena.</div>';
  renderSceneEditor();
}

function renderSceneEditor() {
  const editor = $("#scene-editor");
  if (!editor) return;
  const scene = currentProject?.scenes?.find((item) => item.id === selectedSceneId);
  if (!scene) { editor.hidden = true; return; }
  editor.hidden = false;
  $("#scene-editor-title").textContent = scene.title || "Cena selecionada";
  $("#scene-editor-text").value = scene.text || "";
  $("#scene-editor-duration").value = String(scene.duration_ms || 1000);
  $("#scene-editor-camera").value = scene.camera || "static";
  $("#scene-editor-transition").value = scene.transition || "cut";
  $("#scene-editor-status").textContent = scene.image ? "imagem pronta" : "adicione uma imagem";
}

async function saveSceneEdits() {
  const index = currentProject?.scenes?.findIndex((item) => item.id === selectedSceneId);
  if (index == null || index < 0) return;
  const scenes = currentProject.scenes.map((scene, itemIndex) => itemIndex === index ? { ...scene, text: $("#scene-editor-text").value.trim(), duration_ms: Math.max(100, Number($("#scene-editor-duration").value) || scene.duration_ms || 1000), camera: $("#scene-editor-camera").value, transition: $("#scene-editor-transition").value } : scene);
  currentProject = await api(projectApiPath("/save"), { method: "POST", body: JSON.stringify({ scenes }) });
  renderProjectState(); setStatus("Cena salva");
}

async function moveSelectedScene(direction) {
  const scenes = [...(currentProject?.scenes || [])];
  const index = scenes.findIndex((scene) => scene.id === selectedSceneId);
  const next = index + direction;
  if (index < 0 || next < 0 || next >= scenes.length) return;
  [scenes[index], scenes[next]] = [scenes[next], scenes[index]];
  currentProject = await api(projectApiPath("/save"), { method: "POST", body: JSON.stringify({ scenes }) });
  renderProjectState(); setStatus("Ordem das cenas salva");
}

function renderProjectState() {
  const title = currentProject?.title || "Nenhum projeto";
  $("#active-project-name").textContent = title;
  $("#script-title").value = currentProject?.title || "";
  $("#script-text").value = currentProject?.script || "";
  $("#script-count").textContent = `${($("#script-text").value || "").length} caracteres`;
  $("#script-save-state").textContent = currentProject ? "Projeto carregado" : "Crie um projeto primeiro";
  renderProjectScenes(); renderProjectExports();
  renderCinematicFrame(player?.positionMs || 0);
}

function projectSceneAt(timeMs) {
  const scenes = currentProject?.scenes || [];
  let cursor = 0;
  for (const scene of scenes) {
    const duration = Math.max(100, Number(scene.duration_ms) || 1000);
    if (timeMs <= cursor + duration || scene === scenes.at(-1)) return { scene, localMs: Math.max(0, timeMs - cursor), duration };
    cursor += duration;
  }
  return null;
}

function cinematicImage(scene) {
  if (!scene?.image || !currentProject) return null;
  const url = projectApiPath(`/asset/${encodeURIComponent(scene.image)}`);
  if (!cinematicImages.has(url)) { const image = new Image(); image.src = url; cinematicImages.set(url, image); }
  return cinematicImages.get(url);
}

function renderCinematicFrame(timeMs = 0) {
  if (!previewCanvas || previewMode !== "cinematic") return;
  const context = previewCanvas.getContext("2d"); const width = previewCanvas.width; const height = previewCanvas.height;
  context.fillStyle = "#101827"; context.fillRect(0, 0, width, height);
  const active = projectSceneAt(timeMs);
  if (!active) { context.fillStyle = "#f1d27a"; context.font = "32px sans-serif"; context.fillText("Crie um projeto para visualizar as cenas", 90, height / 2); return; }
  const image = cinematicImage(active.scene);
  if (!image || !image.complete || !image.naturalWidth) { context.fillStyle = "#d7e0ed"; context.font = "28px sans-serif"; context.fillText(active.scene.image ? "Carregando imagem da cena…" : "Adicione uma imagem a esta cena", 90, height / 2); return; }
  const progress = Math.min(1, active.localMs / active.duration); const camera = active.scene.camera || "static";
  const { scale, offsetX, offsetY } = resolveCinematicTransform({ camera, progress, width, height, imageWidth: image.naturalWidth, imageHeight: image.naturalHeight, localMs: active.localMs });
  context.drawImage(image, offsetX, offsetY, image.naturalWidth * scale, image.naturalHeight * scale);
}

async function loadProject(projectId) { currentProject = await api(`/api/projects/${encodeURIComponent(projectId)}`); renderProjectState(); setStatus(`Projeto ${currentProject.title} aberto`); await loadProjectNarration(); }

async function loadProjects() {
  const grid = $("#project-grid"); if (!grid) return;
  const data = await api("/api/projects"); grid.replaceChildren();
  if (!data.projects.length) { $("#project-empty").hidden = false; return; }
  $("#project-empty").hidden = true;
  data.projects.forEach((project) => { const card = document.createElement("article"); card.className = "project-card"; card.innerHTML = `<div class="project-cover cover-night"><span>✦</span></div><div class="project-copy"><div><span class="status-badge stable">local</span><small>${project.updated_at || ""}</small></div><h3></h3><p>${project.scenes?.length || 0} cenas · ${project.narrator?.voice_id || "pm_santa"}</p><button class="text-button" type="button">Abrir produção →</button></div>`; card.querySelector("h3").textContent = project.title; card.querySelector("button").addEventListener("click", () => { void loadProject(project.id).then(() => renderRoute("script")); }); grid.appendChild(card); });
  if (!currentProject) await loadProject(data.projects[0].id);
}

async function createProject() {
  const title = $("#new-project-title").value.trim(); const description = $("#new-project-description").value.trim(); const format = $("#new-project-format").value;
  try { currentProject = await api("/api/projects", { method: "POST", body: JSON.stringify({ title, description, format }) }); $("#project-dialog").hidden = true; renderProjectState(); await loadProjects(); setStatus("Projeto criado e salvo"); renderRoute("script"); } catch (error) { $("#project-dialog-status").textContent = error.message; }
}

async function createExampleProject() {
  try {
    currentProject = await api("/api/projects", { method: "POST", body: JSON.stringify({ title: "A Jornada de uma Estrela", description: "Exemplo original para aprender o fluxo do Fabuloom.", format: "horizontal-1080p" }) });
    const script = "Uma estrela pequena acordou sobre a cidade. Ela procurou um lugar para iluminar e encontrou uma janela aberta. Ao amanhecer, a estrela descobriu que uma boa história também pode ser uma luz.";
    const sentences = script.split(/(?<=[.!?…])\s+/).filter(Boolean);
    currentProject = await api(projectApiPath("/save"), { method: "POST", body: JSON.stringify({ script, scenes: sentences.map((text, index) => ({ id: `scene-${String(index + 1).padStart(3, "0")}`, title: `Cena ${index + 1}`, text, image: null, duration_ms: 3000, camera: "static", transition: "cut" })) }) });
    renderProjectState(); setStatus("Exemplo aberto"); renderRoute("script");
  } catch (error) { setStatus(`Não foi possível abrir o exemplo: ${error.message}`); }
}

async function saveProject() {
  if (!currentProject) { renderRoute("projects"); setStatus("Crie um projeto antes de salvar"); return; }
  const text = $("#script-text").value.trim(); if (!text) { setStatus("Escreva um roteiro antes de salvar"); return; }
  const sentences = text.split(/(?<=[.!?…])\s+|\n+/).map((item) => item.trim()).filter(Boolean);
  const scenes = sentences.map((item, index) => { const previous = currentProject.scenes?.[index] || {}; return { id: previous.id || `scene-${String(index + 1).padStart(3, "0")}`, title: previous.title || `Cena ${index + 1}`, text: item, image: previous.image || null, duration_ms: previous.duration_ms || 3000, camera: previous.camera || "static", transition: previous.transition || "cut" }; });
  try { currentProject = await api(projectApiPath("/save"), { method: "POST", body: JSON.stringify({ title: $("#script-title").value.trim() || currentProject.title, script: text, scenes }) }); renderProjectState(); setStatus("Roteiro e cenas salvos"); } catch (error) { setStatus(`Falha ao salvar: ${error.message}`); }
}

async function uploadAsset(file, kind, sceneId = "") {
  if (!currentProject) return setStatus("Crie um projeto antes de importar arquivos");
  if (file.size > 25 * 1024 * 1024) return setStatus("Arquivo maior que o limite de 25 MB");
  const reader = new FileReader(); reader.onload = async () => { try { currentProject = (await api(projectApiPath("/assets"), { method: "POST", body: JSON.stringify({ filename: file.name, mime: file.type, data: String(reader.result).split(",")[1], kind, scene_id: sceneId }) })).project; renderProjectState(); setStatus(`${file.name} importado`); } catch (error) { setStatus(`Importação falhou: ${error.message}`); } }; reader.readAsDataURL(file);
}

async function generateNarration() {
  if (!currentProject) return setStatus("Crie um projeto antes de gerar áudio");
  try { setStatus("Kokoro está gerando a narração…"); currentProject = (await api(projectApiPath("/narration"), { method: "POST", body: JSON.stringify({ text: $("#script-text").value, voice_id: "pm_santa" }) })).project; voiceVerified = true; renderProjectState(); await loadProjectNarration(); setStatus("Narração Santa V5 concluída"); } catch (error) { setStatus(`Narração bloqueada: ${error.message}`); $("#audio-voice-state").textContent = "pm_santa · indisponível"; }
}

async function loadProjectNarration() {
  if (!currentProject) return false;
  const loaded = await loadNarration({ url: projectApiPath("/audio/manifest.json"), voiceId: currentProject.narrator?.voice_id || "pm_santa", characterId: "santa", characterName: "Santa V5" });
  return loaded;
}

async function exportProject() {
  if (!currentProject) return setStatus("Crie um projeto antes de exportar");
  if (exportInProgress) return setStatus("Uma exportação já está em andamento");
  exportInProgress = true;
  const exportButton = $("#export-project-button");
  if (exportButton) { exportButton.disabled = true; exportButton.textContent = "Exportando…"; }
  try {
    const response = await api(projectApiPath("/export"), { method: "POST", body: JSON.stringify({ format: "horizontal-1080p" }) });
    const poll = async () => {
      const status = await api(projectApiPath("/export/status"));
      $("#export-status").textContent = `${status.message || status.state} · ${status.progress || 0}%`;
      if (status.state === "completed") { currentProject = await api(`/api/projects/${encodeURIComponent(currentProject.id)}`); renderProjectState(); $("#export-status").textContent = "MP4 concluído. Abra o arquivo na lista acima."; exportInProgress = false; if (exportButton) { exportButton.disabled = false; exportButton.textContent = "Exportar MP4"; } return; }
      if (status.state === "failed" || status.state === "cancelled") { exportInProgress = false; if (exportButton) { exportButton.disabled = false; exportButton.textContent = "Exportar MP4"; } return; }
      window.setTimeout(() => void poll(), 700);
    };
    $("#export-status").textContent = `Exportação iniciada · ${response.job.job_id}`; void poll();
  } catch (error) { exportInProgress = false; if (exportButton) { exportButton.disabled = false; exportButton.textContent = "Exportar MP4"; } $("#export-status").textContent = `Exportação bloqueada: ${error.message}`; }
}

const ROUTE_COPY = Object.freeze({
  dashboard: ["OVERVIEW · FABULOOM STUDIO", "Dê vida às suas histórias.", "Um espaço local para organizar roteiro, voz, cenas e renderização."],
  projects: ["BIBLIOTECA LOCAL", "Projetos", "Produções e exportações disponíveis neste computador."],
  script: ["CONTEÚDO", "Roteiro", "Escreva e organize o texto narrativo antes da composição."],
  scenes: ["COMPOSIÇÃO", "Cenas", "Visualize os perfis de produção e suas cenas medidas."],
  narrators: ["ELENCO OFICIAL", "Narradores", "Personagens prontos para a experiência atual do Studio."],
  audio: ["SOM", "Áudio", "Voz, música, efeitos e limites reais do pipeline local."],
  preview: ["COMPOSIÇÃO AO VIVO", "Prévia", "Veja a composição compartilhada com o Narrator Mode."],
  export: ["SAÍDA", "Exportação", "Arquivos produzidos e validados pelo pipeline existente."],
  settings: ["AMBIENTE LOCAL", "Configurações", "Verifique o ambiente e as opções disponíveis neste computador."],
  dev: ["DESENVOLVIMENTO", "Área DEV", "Laboratórios e referências preservados fora do fluxo principal."],
});

function formatTime(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(Number(milliseconds) || 0) / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(Math.floor(totalSeconds % 60)).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function setStatus(message) {
  const label = $("#save-label");
  if (label) label.textContent = message;
}

function renderRoute(route) {
  if (!ROUTE_COPY[route]) return;
  activeRoute = route;
  const [eyebrow, title, subtitle] = ROUTE_COPY[route] || ROUTE_COPY.dashboard;
  $("#page-eyebrow").textContent = eyebrow;
  $("#page-title").textContent = title;
  $("#page-subtitle").textContent = subtitle;
  $("#page-crumb").textContent = title;
  $$(`[data-view]`).forEach((view) => view.classList.toggle("is-visible", view.dataset.view === route));
  $$(`[data-route]`).forEach((link) => {
    if (link.classList.contains("nav-link")) {
      link.classList.toggle("is-active", link.dataset.route === route);
      if (link.dataset.route === route) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
  });
  closeMobileNav();
  if (location.hash !== `#${route}`) history.replaceState(null, "", `#${route}`);
}

function openMobileNav() {
  $("#studio-sidebar")?.classList.add("is-open");
  $("#mobile-backdrop").hidden = false;
  $("#mobile-open")?.setAttribute("aria-expanded", "true");
}

function closeMobileNav() {
  $("#studio-sidebar")?.classList.remove("is-open");
  $("#mobile-backdrop").hidden = true;
  $("#mobile-open")?.setAttribute("aria-expanded", "false");
}

function bindNavigation() {
  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-route]");
    if (!target || target.tagName === "A") {
      if (target?.tagName === "A") {
        event.preventDefault();
        renderRoute(target.dataset.route);
      }
      return;
    }
    event.preventDefault();
    renderRoute(target.dataset.route);
  });
  $("#mobile-open")?.addEventListener("click", openMobileNav);
  $("#mobile-close")?.addEventListener("click", closeMobileNav);
  $("#mobile-backdrop")?.addEventListener("click", closeMobileNav);
  window.addEventListener("hashchange", () => renderRoute(location.hash.slice(1) || "dashboard"));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMobileNav(); });
}

function renderSegment(target, segment, index, className) {
  const row = document.createElement("div");
  row.className = className;
  row.dataset.segmentId = segment.id;
  const number = document.createElement("strong");
  number.className = className.includes("dock") ? "dock-segment-index" : "preview-segment-number";
  number.textContent = String(index + 1).padStart(2, "0");
  const text = document.createElement("span");
  text.className = className.includes("dock") ? "dock-segment-text" : "preview-segment-copy";
  text.textContent = segment.text;
  text.title = segment.text;
  const time = document.createElement(className.includes("dock") ? "span" : "time");
  if (className.includes("dock")) time.className = "dock-segment-time";
  time.textContent = `${formatTime(segment.start_ms)} – ${formatTime(segment.end_ms)}`;
  row.append(number, text, time);
  row.addEventListener("click", () => player?.seek(segment.start_ms));
  target.appendChild(row);
}

function renderSegments(nextManifest) {
  const dockList = $("#dock-timeline-list");
  const previewList = $("#preview-segment-list");
  dockList.replaceChildren();
  previewList.replaceChildren();
  nextManifest.segments.forEach((segment, index) => {
    renderSegment(dockList, segment, index, "dock-segment");
    renderSegment(previewList, segment, index, "preview-segment");
  });
  $("#dock-segment-count").textContent = `${nextManifest.segments.length} segmentos`;
  $("#preview-segment-summary").textContent = `${nextManifest.segments.length} segmentos · ${formatTime(nextManifest.duration_ms)}`;
}

function updateSegmentHighlights(activeSegment) {
  $$("[data-segment-id]").forEach((row) => row.classList.toggle("is-active", Boolean(activeSegment && row.dataset.segmentId === activeSegment.id)));
}

function updatePlaybackUi() {
  const position = player?.positionMs || 0;
  const duration = manifest?.duration_ms || 0;
  const state = player?.state || "stopped";
  $("#preview-seek").max = String(duration);
  $("#preview-seek").value = String(Math.min(position, duration));
  $("#preview-time").textContent = `${formatTime(position)} / ${formatTime(duration)}`;
  $("#canvas-state").textContent = !voiceVerified ? "VERIFICAR" : (({ playing: "REPRODUZINDO", paused: "PAUSADO", ended: "CONCLUÍDO", error: "ERRO" })[state] || "PRONTO");
  updateSegmentHighlights(player?.activeSegment() || null);
}

function updateVoiceIdentity(item, actualVoice = item?.voiceId) {
  const narrator = officialNarratorById(item?.characterId || "santa");
  const name = narrator?.name || "Santa V5";
  const visualStatus = narrator?.status === "production" ? "visual aprovado" : "visual técnico · aguardando arte";
  $("#dock-avatar").textContent = name.slice(0, 1).toUpperCase();
  $("#dock-character-name").textContent = name;
  $("#metric-narrator").textContent = name;
  $("#dock-character-role").textContent = `Narrator Mode V1.4 · ${actualVoice || narrator?.voiceId || "pm_santa"} · pt-BR · ${visualStatus}`;
  $("#canvas-voice").textContent = actualVoice || item?.voiceId || narrator?.voiceId || "pm_santa";
  $("#studio-preview").setAttribute("aria-label", `Prévia do Narrator Mode com ${name}`);
  if (sceneRenderer) sceneRenderer.setNarratorIdentity({ name, voiceId: actualVoice || narrator?.voiceId });
}

async function loadNarration(item) {
  const requested = item || selectedNarration;
  if (!requested) return false;
  selectedNarration = requested;
  const token = ++loadToken;
  setStatus(`Carregando ${requested.voiceId}…`);
  $("#audio-voice-state").textContent = `${requested.voiceId} · carregando`;
  if (player) {
    try { await player.dispose(); } catch (_error) { /* context cleanup is best effort */ }
    player = null;
  }
  manifest = null;
  updatePlaybackUi();
  try {
    const response = await fetch(requested.url, { cache: "no-store" });
    if (!response.ok) throw new Error(`manifesto HTTP ${response.status}`);
    const nextManifest = validateManifest(await response.json());
    const actualVoice = manifestVoiceId(nextManifest);
    if (actualVoice !== requested.voiceId) throw new Error(`voz carregada ${actualVoice || "desconhecida"}, esperado ${requested.voiceId}`);
    const nextPlayer = new AudioTimelinePlayer(nextManifest, {
      onStateChange: (state, error) => {
        if (error) setStatus(`Falha de áudio: ${error.message}`);
        else setStatus(state === "playing" ? `Reproduzindo ${actualVoice}` : `Voz ${actualVoice} · ${state}`);
        updatePlaybackUi();
      },
    });
    await nextPlayer.load();
    if (token !== loadToken) {
      await nextPlayer.dispose();
      return false;
    }
    const narrator = officialNarratorById(requested.characterId || "santa");
    if (!avatarRenderer) throw new Error("renderer visual ainda não está pronto");
    await avatarRenderer.setPack(createOfficialNarratorAvatarPack(requested.characterId || "santa"));
    if (token !== loadToken) {
      await nextPlayer.dispose();
      return false;
    }
    manifest = nextManifest;
    player = nextPlayer;
    activeNarrator = narrator || activeNarrator;
    sceneRenderer.timeline = createNarratorTimeline(nextManifest);
    updateVoiceIdentity(requested, actualVoice);
    renderSegments(nextManifest);
    $("#canvas-voice").textContent = actualVoice;
    $("#metric-voice").textContent = `Kokoro · ${actualVoice}`;
    $("#audio-voice-state").textContent = `${actualVoice} · ${voiceVerified ? "pronta" : "prévia carregada; verifique"}`;
    setStatus(voiceVerified ? `Voz ${actualVoice} pronta` : `Prévia ${actualVoice} carregada; geração requer verificação`);
    updatePlaybackUi();
    return true;
  } catch (error) {
    if (token !== loadToken) return false;
    $("#audio-voice-state").textContent = `${requested.voiceId} · indisponível`;
    setStatus(`Áudio indisponível: ${error.message}`);
    $("#dock-timeline-list").replaceChildren(Object.assign(document.createElement("div"), { className: "loading-row", textContent: "Manifesto ou WAV local indisponível." }));
    $("#preview-segment-list").replaceChildren(Object.assign(document.createElement("div"), { className: "loading-row", textContent: "Não foi possível carregar os segmentos desta voz." }));
    updatePlaybackUi();
    return false;
  }
}

function bindPlayback() {
  $("#preview-play").addEventListener("click", async () => {
    try { await player?.play(); } catch (error) { setStatus(`Falha ao reproduzir: ${error.message}`); }
  });
  $("#preview-pause").addEventListener("click", () => player?.pause());
  $("#preview-stop").addEventListener("click", () => player?.stop());
  $("#preview-seek").addEventListener("input", (event) => player?.seek(Number(event.target.value)));
  const voiceSelect = $("#audio-voice-select");
  voiceSelect.replaceChildren();
  TOPAZIO_NARRATION_CATALOG.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.url;
    option.textContent = `${item.characterName} · ${item.voiceId}`;
    voiceSelect.appendChild(option);
  });
  voiceSelect.addEventListener("change", () => loadNarration(narrationForUrl(voiceSelect.value)));
  voiceSelect.value = selectedNarration.url;
}

function bindNarratorControls() {
  $$('[data-narrator]').forEach((button) => {
    button.addEventListener("click", () => {
      const narrator = officialNarratorById(button.dataset.narrator);
      const narration = narrator ? narrationForCharacter(narrator.id) : null;
      if (!narration) return;
      $("#audio-voice-select").value = narration.url;
      void loadNarration(narration);
      renderRoute("preview");
    });
  });
}

function renderProfiles() {
  const list = $("#scene-list");
  list.replaceChildren();
  PRODUCTION_PROFILES.forEach(async (profile, profileIndex) => {
    const row = document.createElement("div");
    row.className = "scene-row";
    row.innerHTML = `<span class="scene-number">${String(profileIndex + 1).padStart(2, "0")}</span><span><strong>${profile.label}</strong><small>Perfil ${profile.kind} · consultando dados reais…</small></span><span class="scene-meta">local</span>`;
    list.appendChild(row);
    try {
      const response = await fetch(profile.path, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const sceneCount = Array.isArray(data.scenes) ? data.scenes.length : 0;
      row.querySelector("small").textContent = `${sceneCount} cenas · ${formatTime(data.duration_ms || 0)} · ${data.audio?.voice_id || "voz não informada"}`;
      row.querySelector(".scene-meta").textContent = "verificado";
    } catch (_error) {
      row.querySelector("small").textContent = "Perfil não encontrado neste workspace";
      row.querySelector(".scene-meta").textContent = "indisponível";
    }
  });
}

function renderExports() {
  const list = $("#export-list");
  if (!list) return;
  PRODUCTION_EXPORTS.forEach((item) => {
    const row = document.createElement("div");
    row.className = "export-row";
    row.innerHTML = `<span><strong>${item.label} · ${item.variant}</strong><small>${item.format} · arquivo local</small></span><a href="${item.href}" target="_blank" rel="noreferrer">Abrir arquivo ↗</a>`;
    list.appendChild(row);
  });
}

function renderDevLinks() {
  const list = $("#dev-list");
  DEV_LINKS.forEach((item) => {
    const row = document.createElement("div");
    row.className = "dev-row";
    row.innerHTML = `<span><strong>${item.label}</strong><small>${item.note}</small></span><a href="${item.href}">Abrir laboratório ↗</a>`;
    list.appendChild(row);
  });
}

function bindScriptDraft() {
  const title = $("#script-title");
  const text = $("#script-text");
  const count = $("#script-count");
  const updateCount = () => { count.textContent = `${text.value.length} caracteres`; };
  title.addEventListener("input", updateCount); text.addEventListener("input", updateCount); updateCount();
  $("#save-project-button")?.addEventListener("click", () => void saveProject());
  $("#new-project-button")?.addEventListener("click", () => { $("#project-dialog").hidden = false; $("#new-project-title").focus(); });
  $("#project-dialog-close")?.addEventListener("click", () => { $("#project-dialog").hidden = true; });
  $("#project-dialog-submit")?.addEventListener("click", () => void createProject());
  $("#generate-narration-button")?.addEventListener("click", () => void generateNarration());
  $("#export-project-button")?.addEventListener("click", () => void exportProject());
  $("#music-file")?.addEventListener("change", (event) => { const file = event.target.files?.[0]; if (file) void uploadAsset(file, "music"); });
  $$('[data-action="new-project"]').forEach((button) => button.addEventListener("click", () => { renderRoute("projects"); $("#project-dialog").hidden = false; $("#new-project-title").focus(); }));
  $$('[data-action="example"]').forEach((button) => button.addEventListener("click", () => void createExampleProject()));
  $("#scene-save-button")?.addEventListener("click", () => void saveSceneEdits());
  $("#scene-up-button")?.addEventListener("click", () => void moveSelectedScene(-1));
  $("#scene-down-button")?.addEventListener("click", () => void moveSelectedScene(1));
  $("#refresh-health-button")?.addEventListener("click", () => void loadHealth());
  $("#preview-mode-cinematic")?.addEventListener("click", () => { previewMode = "cinematic"; setStatus("Prévia cinematográfica"); renderCinematicFrame(player?.positionMs || 0); });
  $("#preview-mode-narrator")?.addEventListener("click", () => { previewMode = "narrator"; setStatus("Narrator Mode"); });
}

async function loadHealth() {
  const target = $("#settings-health");
  if (!target) return;
  target.innerHTML = '<div class="loading-row">Verificando ambiente…</div>';
  try {
    const health = await api("/api/health");
    const voiceReady = health.voice === "PRONTO";
    voiceVerified = voiceReady;
    $("#canvas-state").textContent = voiceReady ? "PRONTO" : "VERIFICAR";
    $("#canvas-voice").textContent = voiceReady ? "pm_santa" : "pm_santa · configurar";
    $("#kokoro-status")?.replaceChildren(Object.assign(document.createElement("span"), { textContent: voiceReady ? "Voz verificada para geração" : "Voz ainda precisa de verificação real" }));
    const rows = [["Python", `${health.python} · ${health.python_state}`, health.python_state === "PRONTO"], ["FFmpeg", health.ffmpeg_state, health.ffmpeg], ["FFprobe", health.ffprobe_state, health.ffprobe], ["Kokoro", health.kokoro_state, health.kokoro], ["Modelo Kokoro-82M", health.model_state, health.model], ["Voz pm_santa", health.voice, health.voice === "PRONTO"], ["Projetos", health.writable_state, health.writable], ["Diretório", health.workspace, true], ["Porta local", String(health.port), true]];
    target.replaceChildren(...rows.map(([label, value, ok]) => { const row = document.createElement("div"); row.className = "capability-line"; row.innerHTML = `<span>${label}</span><b class="${ok ? "metric-ok" : "status-badge pending"}">${value}</b>`; return row; }));
  } catch (error) { target.textContent = `Não foi possível verificar o ambiente: ${error.message}`; }
}

function startRenderer() {
  return new Promise((resolve) => {
    const ready = async () => {
      try {
        avatarRenderer = new NarratorAvatarRenderer(previewCanvas, { characterId: "santa" });
        await avatarRenderer.load();
        sceneRenderer = new NarratorSceneRenderer(previewCanvas, avatarRenderer, {
          sceneImage,
          amplitudeAt: () => player?.amplitude() || 0,
          narratorName: "Santa V5",
          voiceId: "pm_santa",
        });
        resolve(true);
      } catch (error) {
        setStatus(`Preview indisponível: ${error.message}`);
        resolve(false);
      }
    };
    if (sceneImage.complete) void ready();
    else sceneImage.addEventListener("load", () => void ready(), { once: true });
    sceneImage.addEventListener("error", () => void ready(), { once: true });
  });
}

function animationFrame(timeMs) {
  player?.tick();
  if (previewMode === "cinematic") renderCinematicFrame(player?.positionMs || timeMs);
  else if (sceneRenderer) sceneRenderer.renderFrame({ timeMs: player?.positionMs || timeMs, isPlaying: player?.state === "playing" });
  updatePlaybackUi();
  requestAnimationFrame(animationFrame);
}

async function init() {
  bindNavigation();
  bindPlayback();
  bindNarratorControls();
  bindScriptDraft();
  try { await loadProjects(); } catch (error) { setStatus(`Projetos indisponíveis: ${error.message}`); }
  renderProfiles();
  renderExports();
  renderDevLinks();
  await loadHealth();
  await startRenderer();
  if (!manifest) await loadNarration(selectedNarration);
  renderRoute(location.hash.slice(1) || "dashboard");
  window.__FABULOOM_STUDIO__ = Object.freeze({
    getState: () => Object.freeze({ route: activeRoute, characterId: activeNarrator?.id || "santa", voiceId: manifestVoiceId(manifest), playerState: player?.state || "stopped", durationMs: manifest?.duration_ms || 0 }),
    navigate: renderRoute,
    loadNarration,
  });
  requestAnimationFrame(animationFrame);
}

window.addEventListener("beforeunload", () => { void player?.dispose(); });
void init();
