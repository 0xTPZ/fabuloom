export const VISUAL_QA_PLAN_FORMAT = "fabuloom.visual-qa-plan/0.1";

function safeTime(value) { return Math.max(0, Math.round(Number(value) || 0)); }

function addFrame(frames, frame) {
  const normalized = { close: "full", speechAmplitude: 0, ...frame, timeMs: safeTime(frame.timeMs) };
  if (frames.some((candidate) => candidate.name === normalized.name)) return;
  frames.push(normalized);
}

function addClipFrames(frames, clip, { mode, sequence, prefix, label }) {
  const keyframes = clip?.keyframes || [];
  for (let index = 0; index < keyframes.length; index += 1) {
    const keyframe = keyframes[index];
    const previous = keyframes[index - 1];
    addFrame(frames, {
      name: `${prefix}-kf-${String(index).padStart(2, "0")}`,
      mode,
      sequence,
      timeMs: keyframe.timeMs,
      reason: `${label}: keyframe ${index}; extremos de canais e trocas de pose são inspecionados sem rótulo de defeito`,
    });
    if (previous) {
      addFrame(frames, {
        name: `${prefix}-mid-${String(index - 1).padStart(2, "0")}`,
        mode,
        sequence,
        timeMs: (previous.timeMs + keyframe.timeMs) / 2,
        reason: `${label}: quadro intermediário entre keyframes ${index - 1} e ${index}`,
      });
    }
  }
  addFrame(frames, { name: `${prefix}-end`, mode, sequence, timeMs: clip?.durationMs || 0, reason: `${label}: fim da animação e retorno à pose final` });
}

export function buildSantaV5QaPlan({ waveClip, pointClip } = {}) {
  if (!waveClip || !pointClip) throw new TypeError("waveClip and pointClip are required");
  const captures = [];
  addFrame(captures, { name: "neutral", mode: "neutral", timeMs: 0, reason: "baseline técnico da mesma execução" });
  addFrame(captures, { name: "idle-rest", mode: "neutral", timeMs: 0, sequence: "IDLE", reason: "início do estado de repouso" });
  addFrame(captures, { name: "idle-mid", mode: "neutral", timeMs: 2000, sequence: "IDLE", reason: "quadro intermediário de repouso/respiração" });
  addFrame(captures, { name: "idle-late", mode: "neutral", timeMs: 4000, sequence: "IDLE", reason: "fim da amostra de repouso" });
  addFrame(captures, { name: "face-close", mode: "neutral", timeMs: 0, close: "face", reason: "recorte ampliado do rosto neutro" });
  addFrame(captures, { name: "blink", mode: "blink", timeMs: 4330, close: "face", reason: "mudança de expressão: olhos fechados" });
  addFrame(captures, { name: "mouth-open", mode: "mouth", timeMs: 1200, close: "face", speechAmplitude: 0.92, reason: "mudança de expressão: boca RMS aberta" });
  addClipFrames(captures, waveClip, { mode: "wave", sequence: "WAVE_HELLO", prefix: "wave", label: "WAVE_HELLO" });
  addFrame(captures, { name: "wave-raised", mode: "wave", sequence: "WAVE_HELLO", timeMs: 1680, reason: "WAVE_HELLO: pose extrema e troca para mão de aceno" });
  addFrame(captures, { name: "wave-return", mode: "wave", sequence: "WAVE_HELLO", timeMs: waveClip.durationMs, reason: "WAVE_HELLO: retorno ao repouso" });
  addClipFrames(captures, pointClip, { mode: "point", sequence: "POINT_AT", prefix: "point", label: "POINT_AT" });
  addFrame(captures, { name: "point-approach", mode: "point", sequence: "POINT_AT", timeMs: 1000, reason: "POINT_AT: aproximação do alvo" });
  addFrame(captures, { name: "point-hold", mode: "point", sequence: "POINT_AT", timeMs: 5200, reason: "POINT_AT: contato/hold do alvo" });
  addClipFrames(captures, pointClip, { mode: "point-left", sequence: "POINT_AT", prefix: "point-left", label: "POINT_AT braço esquerdo" });
  addFrame(captures, { name: "point-left-approach", mode: "point-left", sequence: "POINT_AT", timeMs: 1000, reason: "POINT_AT braço esquerdo: aproximação do alvo" });
  addFrame(captures, { name: "point-left-hold", mode: "point-left", sequence: "POINT_AT", timeMs: 5200, reason: "POINT_AT braço esquerdo: contato/hold do alvo" });
  addFrame(captures, { name: "feet-neutral", mode: "neutral", timeMs: 0, reason: "inspeção de contato visual dos pés com o chão" });
  return {
    format: VISUAL_QA_PLAN_FORMAT,
    character: "topazio-narrator-santa-v5",
    renderer: "SantaV5SceneRenderer → LayeredCharacterRenderer",
    selectionPolicy: "start/end, keyframes, intermediates, extrema, asset switches, contacts and facial states",
    captures,
  };
}
