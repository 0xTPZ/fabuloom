import { AudioTimelinePlayer } from "./audio.ts";
import { CanvasCharacterRenderer, CharacterRig } from "./character.ts";
import { validateManifest } from "./timeline.ts";

const NARRATIONS = [
  {
    id: "kokoro-story-demo-0051",
    label: "Lia e a lanterna azul — demonstração",
    url: "/exports/kokoro-story-demo-0051.json",
  },
];

const canvas = document.querySelector("#stage");
const narrationSelect = document.querySelector("#narration-select");
const playButton = document.querySelector("#play");
const pauseButton = document.querySelector("#pause");
const stopButton = document.querySelector("#stop");
const seekInput = document.querySelector("#seek");
const timeLabel = document.querySelector("#time-label");
const stateLabel = document.querySelector("#state-label");
const statusLabel = document.querySelector("#status-label");
const diagnostics = document.querySelector("#diagnostics");

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

function updateUi(state = player?.state || "stopped") {
  const position = player?.positionMs || 0;
  const duration = manifest?.duration_ms || 0;
  seekInput.max = String(duration);
  seekInput.value = String(position);
  timeLabel.textContent = `${formatTime(position)} / ${formatTime(duration)}`;
  stateLabel.textContent = state;
  playButton.disabled = !player || state === "playing" || state === "error";
  pauseButton.disabled = !player || state !== "playing";
  stopButton.disabled = !player || state === "stopped";
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
  statusLabel.textContent = "Carregando manifesto e áudio…";
  updateUi("stopped");
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`manifesto HTTP ${response.status}`);
    manifest = validateManifest(await response.json());
    player = new AudioTimelinePlayer(manifest, {
      onStateChange: (state, error) => {
        if (error) {
          statusLabel.textContent = error.message;
        } else if (state === "playing") {
          statusLabel.textContent = "Reproduzindo narração local.";
        } else if (state === "paused") {
          statusLabel.textContent = "Narração pausada; relógio preservado.";
        } else if (state === "stopped") {
          statusLabel.textContent = "Narração parada.";
        } else if (state === "ended") {
          statusLabel.textContent = "Narração concluída.";
        }
        updateUi(state);
      },
    });
    await player.load();
    statusLabel.textContent = "Pronto para reprodução local.";
    showDiagnostics();
    updateUi("stopped");
  } catch (error) {
    player = null;
    manifest = null;
    statusLabel.textContent = `Falha: ${error.message}`;
    diagnostics.textContent = "Não foi possível carregar esta narração.";
    updateUi("error");
  }
}

playButton.addEventListener("click", async () => {
  try {
    await player.play();
    statusLabel.textContent = "Reproduzindo narração local.";
  } catch (error) {
    statusLabel.textContent = `Falha de reprodução: ${error.message}`;
  }
});
pauseButton.addEventListener("click", () => player?.pause());
stopButton.addEventListener("click", () => player?.stop());
seekInput.addEventListener("input", () => player?.seek(Number(seekInput.value)));
narrationSelect.addEventListener("change", () => loadNarration(narrationSelect.value));

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
