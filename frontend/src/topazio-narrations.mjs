/** Local narration catalog for the official Topazio narrator voices. */

export const TOPAZIO_NARRATION_CATALOG = Object.freeze([
  Object.freeze({
    characterId: "dora",
    characterName: "Dora",
    voiceId: "pf_dora",
    label: "Demonstração · Dora · pf_dora",
    url: "/exports/kokoro-story-demo-0091-dora.json",
  }),
  Object.freeze({
    characterId: "santa",
    characterName: "Santa",
    voiceId: "pm_santa",
    label: "Demonstração · Santa · pm_santa",
    url: "/exports/kokoro-story-demo-0091-santa.json",
  }),
  Object.freeze({
    characterId: "alex",
    characterName: "Alex",
    voiceId: "pm_alex",
    label: "Demonstração · Alex · pm_alex",
    url: "/exports/kokoro-story-demo-0091-alex.json",
  }),
]);

export function narrationForCharacter(characterId) {
  return TOPAZIO_NARRATION_CATALOG.find((item) => item.characterId === characterId) || null;
}

export function narrationForUrl(url) {
  return TOPAZIO_NARRATION_CATALOG.find((item) => item.url === url) || null;
}

export function manifestVoiceId(manifest) {
  const segmentVoice = manifest?.segments?.find((segment) => segment?.voice_id)?.voice_id;
  return manifest?.metadata?.voice_id || segmentVoice || null;
}
