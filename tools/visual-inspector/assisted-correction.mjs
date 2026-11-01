export const ASSISTED_CORRECTION_FORMAT = "fabuloom.assisted-correction/0.1";

export function createCorrectionAttempt({ id, scope, maxAttempts = 1, target = null, evidence = [] } = {}) {
  if (!id || typeof id !== "string") throw new TypeError("correction id is required");
  if (!Number.isInteger(maxAttempts) || maxAttempts < 1) throw new RangeError("maxAttempts must be a positive integer");
  return { format: ASSISTED_CORRECTION_FORMAT, id, scope: scope || "isolated", target, evidence, maxAttempts, attempts: 0, status: "not-started" };
}

/**
 * Apply one isolated correction, validate the result, and always roll back a
 * rejected or failed attempt. The callbacks own their state; this helper does
 * not write files or mutate official assets.
 */
export async function executeCorrectionAttempt({ state, snapshot, apply, validate, rollback } = {}) {
  if (!state || state.format !== ASSISTED_CORRECTION_FORMAT) throw new TypeError("invalid correction state");
  if (typeof snapshot !== "function" || typeof apply !== "function" || typeof validate !== "function" || typeof rollback !== "function") throw new TypeError("snapshot, apply, validate and rollback callbacks are required");
  if (state.attempts >= state.maxAttempts) return { ...state, status: "attempt-limit", lastError: "maximum correction attempts reached" };

  const before = await snapshot();
  const attempts = state.attempts + 1;
  let applied = null;
  try {
    applied = await apply({ before, attempt: attempts });
    const verdict = await validate({ before, after: applied, attempt: attempts });
    if (verdict?.accepted) return { ...state, attempts, status: "accepted", before, applied, verdict };
    await rollback({ before, after: applied, reason: verdict?.reason || "validation rejected the change" });
    return { ...state, attempts, status: "reverted", before, applied, verdict: verdict || { accepted: false } };
  } catch (error) {
    try { await rollback({ before, after: applied, reason: error instanceof Error ? error.message : String(error) }); } catch { /* preserve the original failure */ }
    return { ...state, attempts, status: "reverted", before, applied, error: error instanceof Error ? error.message : String(error) };
  }
}
