import { AudioTimelinePlayer } from "./audio.ts";
import {
  NarratorAvatarRenderer,
  NarratorSceneRenderer,
  createOfficialNarratorAvatarPack,
  createNarratorTimeline,
} from "./narrator-mode.mjs";
import { manifestVoiceId, narrationForCharacter, narrationForUrl, TOPAZIO_NARRATION_CATALOG } from "./topazio-narrations.mjs";
import { validateManifest } from "./timeline.ts";
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

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
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
  (currentProject?.scenes || []).forEach((scene, index) => {
    const row = document.createElement("div"); row.className = "scene-editor-row";
    const number = document.createElement("strong"); number.textContent = String(index + 1).padStart(2, "0");
    const copy = document.createElement("div"); const title = document.createElement("strong"); title.textContent = scene.title || `Cena ${index + 1}`;
    const text = document.createElement("small"); text.textContent = `${scene.text} · ${formatTime(scene.duration_ms || 0)}`; copy.append(title, text);
    const controls = document.createElement("div");
    if (scene.image) { const image = document.createElement("img"); image.src = projectApiPath(`/asset/${encodeURIComponent(scene.image)}`); image.alt = "Imagem da cena"; controls.appendChild(image); }
    const input = document.createElement("input"); input.type = "file"; input.accept = "image/png,image/jpeg,image/webp";
    input.addEventListener("change", () => { if (input.files[0]) void uploadAsset(input.files[0], "image", scene.id); }); controls.appendChild(input);
    row.append(number, copy, controls); list.appendChild(row);
  });
  if (!currentProject?.scenes?.length) list.innerHTML = '<div class="loading-row">Salve um roteiro para criar a primeira cena.</div>';
}

function renderProjectState() {
  const title = currentProject?.title || "Nenhum projeto";
  $("#active-project-name").textContent = title;
  $("#script-title").value = title;
  $("#script-text").value = currentProject?.script || "";
  $("#script-count").textContent = `${($("#script-text").value || "").length} caracteres`;
  $("#script-save-state").textContent = currentProject ? "Projeto carregado" : "Crie um projeto primeiro";
  renderProjectScenes(); renderProjectExports();
}

async function loadProject(projectId) { currentProject = await api(`/api/projects/${encodeURIComponent(projectId)}`); renderProjectState(); setStatus(`Projeto ${currentProject.title} aberto`); }

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

async function saveProject() {
  if (!currentProject) { renderRoute("projects"); setStatus("Crie um projeto antes de salvar"); return; }
  const text = $("#script-text").value.trim(); if (!text) { setStatus("Escreva um roteiro antes de salvar"); return; }
  const sentences = text.split(/(?<=[.!?…])\s+|\n+/).map((item) => item.trim()).filter(Boolean);
  const scenes = sentences.map((item, index) => ({ id: `scene-${String(index + 1).padStart(3, "0")}`, title: `Cena ${index + 1}`, text: item, image: currentProject.scenes?.[index]?.image || null, duration_ms: 3000, camera: "static", transition: "cut" }));
  try { currentProject = await api(projectApiPath("/save"), { method: "POST", body: JSON.stringify({ title: $("#script-title").value.trim() || currentProject.title, script: text, scenes }) }); renderProjectState(); setStatus("Roteiro e cenas salvos"); } catch (error) { setStatus(`Falha ao salvar: ${error.message}`); }
}

async function uploadAsset(file, kind, sceneId = "") {
  if (!currentProject) return setStatus("Crie um projeto antes de importar arquivos");
  if (file.size > 25 * 1024 * 1024) return setStatus("Arquivo maior que o limite de 25 MB");
  const reader = new FileReader(); reader.onload = async () => { try { currentProject = (await api(projectApiPath("/assets"), { method: "POST", body: JSON.stringify({ filename: file.name, mime: file.type, data: String(reader.result).split(",")[1], kind, scene_id: sceneId }) })).project; renderProjectState(); setStatus(`${file.name} importado`); } catch (error) { setStatus(`Importação falhou: ${error.message}`); } }; reader.readAsDataURL(file);
}

async function generateNarration() {
  if (!currentProject) return setStatus("Crie um projeto antes de gerar áudio");
  try { setStatus("Kokoro está gerando a narração…"); currentProject = (await api(projectApiPath("/narration"), { method: "POST", body: JSON.stringify({ text: $("#script-text").value, voice_id: "pm_santa" }) })).project; renderProjectState(); setStatus("Narração Santa V5 concluída"); } catch (error) { setStatus(`Narração bloqueada: ${error.message}`); $("#audio-voice-state").textContent = "pm_santa · indisponível"; }
}

async function exportProject() {
  if (!currentProject) return setStatus("Crie um projeto antes de exportar");
  try {
    const response = await api(projectApiPath("/export"), { method: "POST", body: JSON.stringify({ format: "horizontal-1080p" }) });
    const poll = async () => {
      const status = await api(projectApiPath("/export/status"));
      $("#export-status").textContent = `${status.message || status.state} · ${status.progress || 0}%`;
      if (status.state === "completed") { currentProject = await api(`/api/projects/${encodeURIComponent(currentProject.id)}`); renderProjectState(); $("#export-status").textContent = "MP4 concluído. Abra o arquivo na lista acima."; return; }
      if (status.state === "failed" || status.state === "cancelled") return;
      window.setTimeout(() => void poll(), 700);
    };
    $("#export-status").textContent = `Exportação iniciada · ${response.job.job_id}`; void poll();
  } catch (error) { $("#export-status").textContent = `Exportação bloqueada: ${error.message}`; }
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
  if (!sectionById(route) && route !== "dev") return;
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
  $("#canvas-state").textContent = ({ playing: "REPRODUZINDO", paused: "PAUSADO", ended: "CONCLUÍDO", error: "ERRO" })[state] || "PRONTO";
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
    $("#audio-voice-state").textContent = `${actualVoice} · pronta`;
    setStatus(`Voz ${actualVoice} pronta`);
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
  if (sceneRenderer) sceneRenderer.renderFrame({ timeMs: player?.positionMs || timeMs, isPlaying: player?.state === "playing" });
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
  await startRenderer();
  await loadNarration(selectedNarration);
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
