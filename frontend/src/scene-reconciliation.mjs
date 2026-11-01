function normalizeSceneText(value) {
  return String(value || "").trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

export function reconcileSceneDrafts(existing, texts, idFactory = (index) => `scene-new-${String(index + 1).padStart(3, "0")}`) {
  const previous = Array.isArray(existing) ? existing : [];
  const drafts = Array.isArray(texts) ? texts : [];
  const used = new Set();
  const matches = new Map();
  const byText = new Map();
  previous.forEach((scene, index) => {
    const key = normalizeSceneText(scene.text);
    if (!key) return;
    const list = byText.get(key) || []; list.push(index); byText.set(key, list);
  });
  drafts.forEach((text, index) => {
    const candidates = (byText.get(normalizeSceneText(text)) || []).filter((item) => !used.has(item));
    if (candidates.length === 1) { matches.set(index, candidates[0]); used.add(candidates[0]); }
  });
  // A positional fallback is safe only for one remaining old scene and one
  // remaining draft. More than one unresolved item is structural ambiguity:
  // do not silently move an image or camera setting to another story beat.
  const unresolvedDrafts = drafts.map((_, index) => index).filter((index) => !matches.has(index));
  const unresolvedOld = previous.map((_, index) => index).filter((index) => !used.has(index));
  if (unresolvedDrafts.length === 1 && unresolvedOld.length === 1) {
    matches.set(unresolvedDrafts[0], unresolvedOld[0]); used.add(unresolvedOld[0]);
  }
  const scenes = drafts.map((text, index) => {
    const oldIndex = matches.get(index); const old = oldIndex == null ? null : previous[oldIndex];
    return { id: old?.id || idFactory(index), title: old?.title || `Cena ${index + 1}`, text, image: old?.image || null, duration_ms: old?.duration_ms || 3000, camera: old?.camera || "static", transition: old?.transition || "cut" };
  });
  const removed = previous.filter((_, index) => !used.has(index));
  return { scenes, removed };
}
