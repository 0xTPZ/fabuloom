import { AudioTimelinePlayer } from "./audio.ts";
import { CanvasCharacterRenderer, CharacterRig } from "./character.ts";
import { FANTASY_NARRATOR_PACK } from "./fantasy-narrator-pack.mjs";
import { LayeredCharacterRenderer, LayeredCharacterRig } from "./layered-character.ts";
import { validateCharacterPack } from "./character-pack.mjs";
import { SantaV3Rig, SantaV3SceneRenderer } from "./santa-v3-engine.ts";
import { SANTA_V3_PACK } from "./santa-v3-pack.mjs";
import { SantaV4Rig, SantaV4SceneRenderer } from "./santa-v4-engine.ts";
import { SANTA_V4_PACK } from "./santa-v4-pack.mjs";
import { SantaV5Rig, SantaV5SceneRenderer } from "./santa-v5-engine.ts";
import { SANTA_V5_PACK } from "./santa-v5-pack.mjs";
import { TOPAZIO_NARRATION_CATALOG, manifestVoiceId, narrationForCharacter, narrationForUrl } from "./topazio-narrations.mjs";
import { TOPAZIO_NARRATOR_PACKS } from "./topazio-narrator-packs.mjs";
import { validateManifest } from "./timeline.ts";

const NARRATIONS = TOPAZIO_NARRATION_CATALOG;

const canvas = document.querySelector("#stage");
const narrationSelect = document.querySelector("#narration-select");
const playButton = document.querySelector("#play");
const pauseButton = document.querySelector("#pause");
const stopButton = document.querySelector("#stop");
const seekInput = document.querySelector("#seek");
const seekEnd = document.querySelector("#seek-end");
const timeLabel = document.querySelector("#time-label");
const overlayTime = document.querySelector("#overlay-time");
const stateLabel = document.querySelector("#state-label");
const stageStatusText = document.querySelector("#stage-status-text");
const statusLabel = document.querySelector("#status-label");
const diagnostics = document.querySelector("#diagnostics");
const timelineList = document.querySelector("#timeline-list");
const segmentCount = document.querySelector("#segment-count");
const activeSegmentLabel = document.querySelector("#active-segment");
const characterState = document.querySelector("#character-state");
const characterSelect = document.querySelector("#character-select");
const expressionSelect = document.querySelector("#expression-select");
const characterName = document.querySelector("#character-name");
const characterKind = document.querySelector("#character-kind");
const characterMotion = document.querySelector("#character-motion");
const presenceAvatar = document.querySelector("#presence-avatar");
const presenceName = document.querySelector("#presence-name");
const presenceKind = document.querySelector("#presence-kind");
const voiceAvatar = document.querySelector("#voice-avatar");
const voiceLanguage = document.querySelector("#voice-language");
const voiceLoaded = document.querySelector("#voice-loaded");
const sidebar = document.querySelector("#sidebar");
const sidebarToggle = document.querySelector("#sidebar-toggle");
const sidebarClose = document.querySelector("#sidebar-close");
const sidebarBackdrop = document.querySelector("#sidebar-backdrop");

const geometricRig = new CharacterRig();
const layeredRig = new LayeredCharacterRig();
const geometricRenderer = new CanvasCharacterRenderer(canvas, geometricRig);
const layeredRenderer = new LayeredCharacterRenderer(canvas, layeredRig, FANTASY_NARRATOR_PACK);
const santaV3Rig = new SantaV3Rig();
const santaV3Renderer = new SantaV3SceneRenderer(canvas, santaV3Rig);
const santaV4Rig = new SantaV4Rig();
const santaV4Renderer = new SantaV4SceneRenderer(canvas, santaV4Rig);
const santaV5Rig = new SantaV5Rig();
const santaV5Renderer = new SantaV5SceneRenderer(canvas, santaV5Rig);
const narratorKeys = Object.keys(TOPAZIO_NARRATOR_PACKS);
const narratorRigs = Object.fromEntries(narratorKeys.map((key) => [key, new LayeredCharacterRig()]));
const narratorRenderers = Object.fromEntries(narratorKeys.map((key) => [
  key,
  new LayeredCharacterRenderer(canvas, narratorRigs[key], TOPAZIO_NARRATOR_PACKS[key]),
]));
const narratorReady = Object.fromEntries(narratorKeys.map((key) => [key, false]));
let santaV3Ready = false;
let santaV4Ready = false;
let santaV5Ready = false;
let activeRig = narratorRigs.dora;
let activeRenderer = narratorRenderers.dora;
let activeCharacterId = "dora";
let layeredReady = false;
let player = null;
let manifest = null;
let narrationLoadToken = 0;

const characterMeta = {
  geometric: { name: "Lia", kind: "Rig geométrico · Canvas", presence: "Referência técnica", motion: "Respiração sutil" },
  fantasy: { name: "Ari", kind: "Pack em camadas · 2.5D", presence: "Narrador ilustrado", motion: "Cabeça, braços, cabelo e respiração" },
  dora: { name: "Dora", kind: "Narradora oficial · Rig V2", presence: "Voz acolhedora · pf_dora", motion: "Cabeça, braços, mãos, olhos, boca e respiração" },
  santa: { name: "Santa", kind: "Narrador oficial · Rig V2", presence: "Voz sábia · pm_santa", motion: "Cabeça, braços, mãos, olhos, boca e respiração" },
  alex: { name: "Alex", kind: "Narrador oficial · Rig V2", presence: "Voz confiante · pm_alex", motion: "Cabeça, braços, mãos, olhos, boca e respiração" },
  "santa-v3": { name: "Santa V3", kind: "Narrador oficial · Rig completo", presence: "Voz sábia · pm_santa", motion: "Corpo, braços, mãos, pernas, xícara e livro" },
  "santa-v4": { name: "Santa V4", kind: "Narrador oficial · Cartoon 2.5D", presence: "Voz sábia · pm_santa", motion: "Cabeça, braços, mãos, pernas, barba, olhos e respiração" },
  "santa-v5": { name: "Santa V5", kind: "Narrador oficial · Rig final", presence: "Voz sábia · pm_santa", motion: "Cabeça, olhos, boca, braços, mãos, pernas e respiração" },
};

for (const narration of NARRATIONS) {
  const option = document.createElement("option");
  option.value = narration.url;
  option.textContent = narration.label;
  narrationSelect.appendChild(option);
}

function updateCharacterMeta() {
  const meta = characterMeta[activeCharacterId];
  characterName.textContent = meta.name;
  characterKind.textContent = meta.kind;
  characterMotion.textContent = meta.motion;
  if (presenceAvatar) presenceAvatar.textContent = meta.name.slice(0, 1);
  if (presenceName) presenceName.textContent = meta.name;
  if (presenceKind) presenceKind.textContent = meta.presence;
}

function setVoiceInfo({ voiceId = null, providerId = null, language = "pt-BR", state = "waiting" } = {}) {
  if (voiceLanguage) voiceLanguage.textContent = language === "pt-BR" ? "Português brasileiro" : language;
  if (voiceAvatar) voiceAvatar.textContent = voiceId ? voiceId.slice(-1).toUpperCase() : "P";
  if (!voiceLoaded) return;
  if (state === "loading") {
    voiceLoaded.textContent = `Carregando voz: ${voiceId || "desconhecida"}…`;
  } else if (state === "error") {
    voiceLoaded.textContent = `Falha ao carregar voz: ${voiceId || "desconhecida"}`;
  } else if (voiceId) {
    voiceLoaded.textContent = `Voz carregada: ${voiceId} · ${providerId || "provedor desconhecido"}`;
  } else {
    voiceLoaded.textContent = "Voz carregada: aguardando manifesto…";
  }
}

function selectCharacter(characterId, { loadVoice = true } = {}) {
  if (characterId === "fantasy" && !layeredReady) {
    characterSelect.value = "geometric";
    return Promise.resolve(false);
  }
  if (characterId === "santa-v3" && !santaV3Ready) {
    characterSelect.value = "santa";
    return Promise.resolve(false);
  }
  if (characterId === "santa-v4" && !santaV4Ready) {
    characterSelect.value = "santa";
    return Promise.resolve(false);
  }
  if (characterId === "santa-v5" && !santaV5Ready) {
    characterSelect.value = "santa";
    return Promise.resolve(false);
  }
  if (narratorKeys.includes(characterId) && !narratorReady[characterId]) {
    characterSelect.value = layeredReady ? "fantasy" : "geometric";
    return Promise.resolve(false);
  }
  activeCharacterId = characterId;
  if (characterId === "fantasy") {
    activeRig = layeredRig;
    activeRenderer = layeredRenderer;
  } else if (narratorKeys.includes(characterId)) {
    activeRig = narratorRigs[characterId];
    activeRenderer = narratorRenderers[characterId];
  } else if (characterId === "santa-v3") {
    activeRig = santaV3Rig;
    activeRenderer = santaV3Renderer;
  } else if (characterId === "santa-v4") {
    activeRig = santaV4Rig;
    activeRenderer = santaV4Renderer;
  } else if (characterId === "santa-v5") {
    activeRig = santaV5Rig;
    activeRenderer = santaV5Renderer;
  } else {
    activeRig = geometricRig;
    activeRenderer = geometricRenderer;
  }
  if (characterId === "fantasy" || narratorKeys.includes(characterId)) activeRenderer.setExpression(expressionSelect.value);
  else if (characterId === "santa-v3") santaV3Renderer.characterRenderer.setExpression(expressionSelect.value);
  else if (characterId === "santa-v4") santaV4Renderer.characterRenderer.setExpression(expressionSelect.value);
  else if (characterId === "santa-v5") santaV5Renderer.characterRenderer.setExpression(expressionSelect.value);
  updateCharacterMeta();
  updateUi(player?.state || "stopped");
  if (!loadVoice || (!narratorKeys.includes(characterId) && !["santa-v3", "santa-v4", "santa-v5"].includes(characterId))) return Promise.resolve(true);
  const narration = narrationForCharacter(["santa-v3", "santa-v4", "santa-v5"].includes(characterId) ? "santa" : characterId);
  if (!narration) return Promise.resolve(false);
  narrationSelect.value = narration.url;
  return loadNarration(narration);
}

async function prepareLayeredCharacters() {
  const fantasyOption = characterSelect.querySelector('option[value="fantasy"]');
  try {
    validateCharacterPack(FANTASY_NARRATOR_PACK);
    await layeredRenderer.load();
    layeredReady = true;
    fantasyOption.disabled = false;
    fantasyOption.textContent = "Ari · guardião das histórias";
  } catch (_error) {
    fantasyOption.disabled = true;
    fantasyOption.textContent = "Ari · asset indisponível";
    characterKind.textContent = "Pack em camadas · indisponível";
  }
  const santaV4Option = characterSelect.querySelector('option[value="santa-v4"]');
  try {
    validateCharacterPack(SANTA_V4_PACK);
    await santaV4Renderer.characterRenderer.load();
    santaV4Ready = true;
    santaV4Option.disabled = false;
    santaV4Option.textContent = "Santa V4 · pm_santa";
  } catch (_error) {
    santaV4Option.disabled = true;
    santaV4Option.textContent = "Santa V4 · asset indisponível";
  }
  const santaV5Option = characterSelect.querySelector('option[value="santa-v5"]');
  try {
    validateCharacterPack(SANTA_V5_PACK);
    await santaV5Renderer.characterRenderer.load();
    santaV5Ready = true;
    santaV5Option.disabled = false;
    santaV5Option.textContent = "Santa V5 · pm_santa";
  } catch (_error) {
    santaV5Option.disabled = true;
    santaV5Option.textContent = "Santa V5 · asset indisponível";
  }
  for (const key of narratorKeys) {
    const option = characterSelect.querySelector(`option[value="${key}"]`);
    try {
      validateCharacterPack(TOPAZIO_NARRATOR_PACKS[key]);
      await narratorRenderers[key].load();
      narratorReady[key] = true;
      option.disabled = false;
      option.textContent = `${characterMeta[key].name} · ${TOPAZIO_NARRATOR_PACKS[key].voice_id}`;
    } catch (_error) {
      option.disabled = true;
      option.textContent = `${characterMeta[key].name} · asset indisponível`;
    }
  }
  const santaV3Option = characterSelect.querySelector('option[value="santa-v3"]');
  try {
    validateCharacterPack(SANTA_V3_PACK);
    await santaV3Renderer.characterRenderer.load();
    santaV3Ready = true;
    santaV3Option.disabled = false;
    santaV3Option.textContent = "Santa V3 · pm_santa";
  } catch (_error) {
    santaV3Option.disabled = true;
    santaV3Option.textContent = "Santa V3 · asset indisponível";
  }
  if (narratorReady.dora) await selectCharacter("dora");
  else if (layeredReady) await selectCharacter("fantasy", { loadVoice: false });
  else await selectCharacter("geometric", { loadVoice: false });
}

function formatTime(milliseconds) {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function formatClock(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `00:${minutes}:${seconds}`;
}

function setStatus(message) {
  if (!statusLabel) return;
  const dot = statusLabel.querySelector(".status-dot");
  statusLabel.replaceChildren(dot || document.createTextNode(""), document.createTextNode(` ${message}`));
}

function renderTimeline(nextManifest) {
  if (!timelineList || !segmentCount) return;
  timelineList.replaceChildren();
  segmentCount.textContent = `${nextManifest.segments.length} segmentos`;
  if (!nextManifest.segments.length) {
    const empty = document.createElement("div");
    empty.className = "timeline-empty";
    empty.textContent = "Nenhum segmento disponível.";
    timelineList.appendChild(empty);
    return;
  }
  for (const [index, segment] of nextManifest.segments.entries()) {
    const row = document.createElement("div");
    row.className = "timeline-row";
    row.dataset.segmentId = segment.id;

    const number = document.createElement("span");
    number.className = "timeline-index";
    number.textContent = String(index + 1).padStart(2, "0");
    const copy = document.createElement("span");
    copy.className = "timeline-copy";
    copy.textContent = segment.text || `Segmento ${index + 1}`;
    copy.title = copy.textContent;
    const bar = document.createElement("span");
    bar.className = "timeline-bar";
    const barCount = Math.max(5, Math.min(18, Math.round(segment.duration_ms / 620)));
    for (let i = 0; i < barCount; i += 1) {
      const tick = document.createElement("i");
      tick.setAttribute("aria-hidden", "true");
      bar.appendChild(tick);
    }
    const times = document.createElement("span");
    times.className = "timeline-times";
    times.textContent = `${formatTime(segment.start_ms)} – ${formatTime(segment.end_ms)}`;
    row.append(number, copy, bar, times);
    timelineList.appendChild(row);
  }
}

function updateTimelineState(activeSegment) {
  const rows = timelineList?.querySelectorAll(".timeline-row") || [];
  rows.forEach((row) => row.classList.toggle("is-active", Boolean(activeSegment && row.dataset.segmentId === activeSegment.id)));
  if (activeSegmentLabel) activeSegmentLabel.textContent = activeSegment ? (activeSegment.text || "Segmento atual") : "Pausa ou repouso";
}

function updateUi(state = player?.state || "stopped") {
  const position = player?.positionMs || 0;
  const duration = manifest?.duration_ms || 0;
  const activeSegment = player?.activeSegment() || null;
  seekInput.max = String(duration);
  seekInput.value = String(Math.min(position, duration));
  timeLabel.textContent = `${formatTime(position)} / ${formatTime(duration)}`;
  if (seekEnd) seekEnd.textContent = formatTime(duration);
  if (overlayTime) overlayTime.textContent = formatClock(position);
  stateLabel.textContent = state;
  updateTimelineState(activeSegment);
  playButton.disabled = !player || state === "playing" || state === "error";
  pauseButton.disabled = !player || state !== "playing";
  stopButton.disabled = !player || state === "stopped";
  const stageCopy = { playing: "Reproduzindo", paused: "Pausado", stopped: "Palco pronto", ended: "Concluído", error: "Falha de reprodução" }[state] || "Palco pronto";
  const rigCopy = state === "playing" ? (activeSegment ? "Reproduzindo" : "Analisando pausa") : state === "paused" ? "Pausado" : state === "error" ? "Indisponível" : "Repouso";
  if (stageStatusText) stageStatusText.textContent = stageCopy;
  if (characterState) characterState.textContent = rigCopy;
}

function showDiagnostics() {
  if (!manifest) {
    diagnostics.textContent = "Nenhuma narração carregada.";
    return;
  }
  const first = manifest.segments[0] || {};
  const metadata = first.metadata || {};
  const voiceId = manifestVoiceId(manifest);
  setVoiceInfo({
    voiceId,
    providerId: first.provider_id || metadata.provider_id,
    language: first.language || metadata.language || "pt-BR",
    state: voiceId ? "ready" : "error",
  });
  diagnostics.textContent = [
    `manifesto: ${manifest.id}`,
    `segmentos: ${manifest.segments.length}`,
    `provedor: ${first.provider_id || metadata.provider_id || "desconhecido"}`,
    `voz carregada: ${voiceId || "desconhecida"}`,
    `modelo: ${metadata.model_id || "não informado"}`,
    `revisão: ${metadata.model_revision || "não informada"}`,
    `tempo temporal: ${metadata.temporal_source || "measured_wav"}`,
    "alinhamento fonético: indisponível",
    "amplitude: análise RMS em tempo real",
  ].join("\n");
}

async function loadNarration(narration) {
  const loadToken = ++narrationLoadToken;
  const previousPlayer = player;
  player = null;
  manifest = null;
  setVoiceInfo({ voiceId: narration.voiceId, language: "pt-BR", state: "loading" });
  setStatus(`Carregando ${narration.characterName} · ${narration.voiceId}…`);
  updateUi("stopped");
  if (previousPlayer) {
    try {
      await previousPlayer.dispose();
    } catch (error) {
      setStatus(`Reprodução anterior encerrada com aviso: ${error.message}`);
    }
  }
  if (loadToken !== narrationLoadToken) return false;

  try {
    const response = await fetch(narration.url);
    if (!response.ok) throw new Error(`manifesto HTTP ${response.status}`);
    const nextManifest = validateManifest(await response.json());
    const actualVoiceId = manifestVoiceId(nextManifest);
    if (actualVoiceId !== narration.voiceId) {
      throw new Error(`manifesto carregou ${actualVoiceId || "uma voz desconhecida"}, esperado ${narration.voiceId}`);
    }
    if (nextManifest.segments.some((segment) => segment.voice_id !== actualVoiceId)) {
      throw new Error("manifesto contém segmentos de vozes diferentes");
    }
    const nextPlayer = new AudioTimelinePlayer(nextManifest, {
      onStateChange: (state, error) => {
        if (error) setStatus(error.message);
        else if (state === "playing") setStatus(`Reproduzindo ${actualVoiceId}.`);
        else if (state === "paused") setStatus(`Narração ${actualVoiceId} pausada; relógio preservado.`);
        else if (state === "stopped") setStatus(`Narração ${actualVoiceId} parada.`);
        else if (state === "ended") setStatus(`Narração ${actualVoiceId} concluída.`);
        updateUi(state);
      },
    });
    await nextPlayer.load();
    if (loadToken !== narrationLoadToken) {
      await nextPlayer.dispose();
      return false;
    }
    manifest = nextManifest;
    player = nextPlayer;
    narrationSelect.value = narration.url;
    renderTimeline(manifest);
    showDiagnostics();
    setStatus(`Voz ${actualVoiceId} pronta para reprodução.`);
    updateUi("stopped");
    return true;
  } catch (error) {
    if (loadToken !== narrationLoadToken) return false;
    player = null;
    manifest = null;
    setVoiceInfo({ voiceId: narration.voiceId, language: "pt-BR", state: "error" });
    setStatus(`Falha ao carregar ${narration.voiceId}: ${error.message}`);
    diagnostics.textContent = `Não foi possível carregar a voz ${narration.voiceId}.`;
    if (timelineList) timelineList.replaceChildren(Object.assign(document.createElement("div"), { className: "timeline-empty", textContent: `Falha ao carregar ${narration.characterName}: ${error.message}` }));
    if (segmentCount) segmentCount.textContent = "0 segmentos";
    updateUi("error");
    return false;
  }
}

function setSidebarOpen(open) {
  sidebar?.classList.toggle("is-open", open);
  if (sidebarBackdrop) sidebarBackdrop.hidden = !open;
  sidebarToggle?.setAttribute("aria-expanded", String(open));
}

playButton.addEventListener("click", async () => {
  try {
    await player.play();
    setStatus("Reproduzindo narração local.");
  } catch (error) {
    setStatus(`Falha de reprodução: ${error.message}`);
  }
});
pauseButton.addEventListener("click", () => player?.pause());
stopButton.addEventListener("click", () => player?.stop());
seekInput.addEventListener("input", () => player?.seek(Number(seekInput.value)));
narrationSelect.addEventListener("change", () => {
  const narration = narrationForUrl(narrationSelect.value);
  if (!narration) return;
  void (async () => {
    if (narration.characterId !== activeCharacterId) {
      await selectCharacter(narration.characterId, { loadVoice: false });
    }
    await loadNarration(narration);
  })();
});
characterSelect.addEventListener("change", () => { void selectCharacter(characterSelect.value); });
expressionSelect.addEventListener("change", () => {
  if (activeCharacterId === "fantasy") layeredRenderer.setExpression(expressionSelect.value);
  else if (narratorKeys.includes(activeCharacterId)) narratorRenderers[activeCharacterId].setExpression(expressionSelect.value);
  else if (activeCharacterId === "santa-v3") santaV3Renderer.characterRenderer.setExpression(expressionSelect.value);
  else if (activeCharacterId === "santa-v4") santaV4Renderer.characterRenderer.setExpression(expressionSelect.value);
  else if (activeCharacterId === "santa-v5") santaV5Renderer.characterRenderer.setExpression(expressionSelect.value);
});
sidebarToggle?.addEventListener("click", () => setSidebarOpen(true));
sidebarClose?.addEventListener("click", () => setSidebarOpen(false));
sidebarBackdrop?.addEventListener("click", () => setSidebarOpen(false));
document.addEventListener("keydown", (event) => { if (event.key === "Escape") setSidebarOpen(false); });

function frame(timeMs) {
  if (player) {
    player.tick();
    activeRig.setSpeechAmplitude(player.amplitude());
    activeRig.update(timeMs, player.state === "playing");
    updateUi(player.state);
  } else {
    activeRig.setSpeechAmplitude(0);
    activeRig.update(timeMs, false);
  }
  if (["santa-v3", "santa-v4", "santa-v5"].includes(activeCharacterId)) {
    const sceneRenderer = activeCharacterId === "santa-v5" ? santaV5Renderer : activeCharacterId === "santa-v4" ? santaV4Renderer : santaV3Renderer;
    const sceneRig = activeCharacterId === "santa-v5" ? santaV5Rig : activeCharacterId === "santa-v4" ? santaV4Rig : santaV3Rig;
    sceneRig.setSceneDuration(manifest?.duration_ms || 1);
    sceneRenderer.renderFrame({
      timeMs,
      durationMs: manifest?.duration_ms || 1,
      speechAmplitude: player?.amplitude() || 0,
      isPlaying: player?.state === "playing",
    });
  } else {
    activeRenderer.render();
  }
  requestAnimationFrame(frame);
}

async function initializeStage() {
  updateCharacterMeta();
  setVoiceInfo({ language: "pt-BR", state: "waiting" });
  await prepareLayeredCharacters();
}

void initializeStage();
requestAnimationFrame(frame);
