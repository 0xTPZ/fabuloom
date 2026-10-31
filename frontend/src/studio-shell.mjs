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
  const savedTitle = localStorage.getItem("fabuloom.studio.script.title");
  const savedText = localStorage.getItem("fabuloom.studio.script.text");
  if (savedTitle) title.value = savedTitle;
  if (savedText) text.value = savedText;
  const save = () => {
    localStorage.setItem("fabuloom.studio.script.title", title.value);
    localStorage.setItem("fabuloom.studio.script.text", text.value);
    count.textContent = `${text.value.length} caracteres`;
    setStatus("Roteiro salvo localmente");
  };
  title.addEventListener("input", save);
  text.addEventListener("input", save);
  save();
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
