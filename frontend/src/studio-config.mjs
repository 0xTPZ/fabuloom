/** Public Fabuloom Studio shell contract. UI metadata only; renderers remain shared. */

export const STUDIO_UI_FORMAT = "fabuloom.studio-ui/0.1";

export const STUDIO_SECTIONS = Object.freeze([
  Object.freeze({ id: "dashboard", label: "Dashboard", icon: "⌂", status: "stable" }),
  Object.freeze({ id: "projects", label: "Projetos", icon: "▦", status: "stable" }),
  Object.freeze({ id: "script", label: "Roteiro", icon: "≡", status: "experimental" }),
  Object.freeze({ id: "scenes", label: "Cenas", icon: "◇", status: "experimental" }),
  Object.freeze({ id: "narrators", label: "Narradores", icon: "✦", status: "stable" }),
  Object.freeze({ id: "audio", label: "Áudio", icon: "◉", status: "stable" }),
  Object.freeze({ id: "preview", label: "Prévia", icon: "▷", status: "stable" }),
  Object.freeze({ id: "export", label: "Exportação", icon: "⇩", status: "stable" }),
]);

export const DEV_LINKS = Object.freeze([
  Object.freeze({ label: "Character Stage legado", href: "/index.html", note: "V0.3 preservado" }),
  Object.freeze({ label: "Narrator Mode V1.4", href: "/narrator-mode.html", note: "renderer facial oficial" }),
  Object.freeze({ label: "Laboratório facial", href: "/narrator-face-lab.html", note: "diagnóstico" }),
  Object.freeze({ label: "Visual Inspector", href: "/visual-inspector.html", note: "evidência técnica" }),
  Object.freeze({ label: "Visual QA", href: "/visual-qa.html", note: "gate experimental" }),
]);

export const OFFICIAL_NARRATORS = Object.freeze([
  Object.freeze({ id: "santa", name: "Santa V5", voiceId: "pm_santa", role: "Referência principal", tone: "Sábio · solene", status: "production", visualPack: "topazio-narrator-santa-v5" }),
  Object.freeze({ id: "dora", name: "Dora", voiceId: "pf_dora", role: "Narradora oficial", tone: "Acolhedora · serena", status: "awaiting-art-approval", visualPack: "topazio-narrator-dora-v2" }),
  Object.freeze({ id: "alex", name: "Alex", voiceId: "pm_alex", role: "Narrador oficial", tone: "Confiante · amigável", status: "awaiting-art-approval", visualPack: "topazio-narrator-alex-v2" }),
]);

export const PRODUCTION_PROFILES = Object.freeze([
  Object.freeze({ id: "official-promo-v1", label: "Official Promo V1", path: "/exports/official-promo-v1/fabuloom-official-promo-v1-profile.json", kind: "vertical" }),
  Object.freeze({ id: "vertical-story-v1", label: "Vertical Cinematic Story V1", path: "/exports/vertical-story-v1/fabuloom-vertical-story-v1-profile.json", kind: "vertical" }),
]);

export const PRODUCTION_EXPORTS = Object.freeze([
  Object.freeze({ label: "Official Promo V1", variant: "Principal", href: "/exports/videos/fabuloom-official-promo-v1.mp4", format: "1080×1920 · H.264/AAC" }),
  Object.freeze({ label: "Official Promo V1", variant: "TikTok-ready", href: "/exports/videos/fabuloom-official-promo-v1-tiktok-ready.mp4", format: "1080×1920 · sem música" }),
  Object.freeze({ label: "Vertical Cinematic Story V1", variant: "Referência", href: "/exports/videos/fabuloom-vertical-story-test-v1.mp4", format: "1080×1920 · H.264/AAC" }),
  Object.freeze({ label: "Narrator Mode V1.4", variant: "Referência", href: "/exports/videos/fabuloom-narrator-mode-v1.4-neck-fix.mp4", format: "1920×1080 · H.264/AAC" }),
]);

export function sectionById(id) {
  return STUDIO_SECTIONS.find((section) => section.id === id) || null;
}

export function validateStudioSection(id) {
  if (!sectionById(id)) throw new TypeError(`Unknown Studio section: ${id}`);
  return id;
}

export function officialNarratorById(id) {
  return OFFICIAL_NARRATORS.find((narrator) => narrator.id === id) || null;
}
