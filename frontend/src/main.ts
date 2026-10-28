import { AudioTimelinePlayer } from "./audio.ts";
import { CanvasCharacterRenderer, CharacterRig } from "./character.ts";
import { validateManifest } from "./timeline.ts";

const NARRATIONS = [
  { id: "kokoro-story-demo-0051", label: "Lia e a lanterna azul — demonstração", url: "/exports/kokoro-story-demo-0051.json" },
];

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
const sidebar = document.querySelector("#sidebar");
const sidebarToggle = document.querySelector("#sidebar-toggle");
const sidebarClose = document.querySelector("#sidebar-close");
const sidebarBackdrop = document.querySelector("#sidebar-backdrop");

const rig = new CharacterRig();
const renderer = new CanvasCharacterRenderer(canvas, rig);
let player = null;
let manifest = null;

for (const narration of NARRATIONS) {
  const option = document.createElement("option");
  option.value = narration.url;
  option.textContent = narration.label;
  narrationSelect.appendChild(option);
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
  diagnostics.textContent = [
    `manifesto: ${manifest.id}`,
    `segmentos: ${manifest.segments.length}`,
    `provedor: ${first.provider_id || metadata.provider_id || "desconhecido"}`,
    `voz: ${first.voice_id || "desconhecida"}`,
    `modelo: ${metadata.model_id || "não informado"}`,
    `revisão: ${metadata.model_revision || "não informada"}`,
    `tempo temporal: ${metadata.temporal_source || "measured_wav"}`,
    "alinhamento fonético: indisponível",
    "amplitude: análise RMS em tempo real",
  ].join("\n");
}

async function loadNarration(url) {
  if (player) player.dispose();
  player = null;
  manifest = null;
  setStatus("Carregando manifesto e áudio…");
  updateUi("stopped");
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`manifesto HTTP ${response.status}`);
    manifest = validateManifest(await response.json());
    renderTimeline(manifest);
    player = new AudioTimelinePlayer(manifest, {
      onStateChange: (state, error) => {
        if (error) setStatus(error.message);
        else if (state === "playing") setStatus("Reproduzindo narração local.");
        else if (state === "paused") setStatus("Narração pausada; relógio preservado.");
        else if (state === "stopped") setStatus("Narração parada.");
        else if (state === "ended") setStatus("Narração concluída.");
        updateUi(state);
      },
    });
    await player.load();
    setStatus("Pronto para reprodução local.");
    showDiagnostics();
    updateUi("stopped");
  } catch (error) {
    player = null;
    manifest = null;
    setStatus(`Falha: ${error.message}`);
    diagnostics.textContent = "Não foi possível carregar esta narração.";
    if (timelineList) timelineList.replaceChildren(Object.assign(document.createElement("div"), { className: "timeline-empty", textContent: "Falha ao carregar a narração." }));
    if (segmentCount) segmentCount.textContent = "0 segmentos";
    updateUi("error");
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
narrationSelect.addEventListener("change", () => loadNarration(narrationSelect.value));
sidebarToggle?.addEventListener("click", () => setSidebarOpen(true));
sidebarClose?.addEventListener("click", () => setSidebarOpen(false));
sidebarBackdrop?.addEventListener("click", () => setSidebarOpen(false));
document.addEventListener("keydown", (event) => { if (event.key === "Escape") setSidebarOpen(false); });

function frame(timeMs) {
  if (player) {
    player.tick();
    rig.setSpeechAmplitude(player.amplitude());
    rig.update(timeMs, player.state === "playing");
    updateUi(player.state);
  } else {
    rig.setSpeechAmplitude(0);
    rig.update(timeMs, false);
  }
  renderer.render();
  requestAnimationFrame(frame);
}

loadNarration(NARRATIONS[0].url);
requestAnimationFrame(frame);
