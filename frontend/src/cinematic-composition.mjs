/** Shared camera contract used by the browser composition preview.
 * FFmpeg consumes the same persisted fields (camera, duration_ms and image).
 * The browser keeps the calculation pure so it can be regression-tested.
 */
export function resolveCinematicTransform({ camera = "static", progress = 0, width, height, imageWidth, imageHeight, localMs = 0 }) {
  // FFmpeg uses `decrease + pad` for static scenes and `increase + crop`
  // before zoompan for moving scenes. Keep those two framing contracts
  // explicit so portrait and square assets do not silently crop in Canvas.
  const baseScale = camera === "static"
    ? Math.min(width / imageWidth, height / imageHeight)
    : Math.max(width / imageWidth, height / imageHeight);
  let scale = baseScale; let offsetX = (width - imageWidth * scale) / 2; let offsetY = (height - imageHeight * scale) / 2;
  if (camera !== "static") {
    const zoom = camera === "zoom" ? 1 + Math.min(0.12, localMs / 1000 * 0.0015 * 30) : 1.08;
    scale *= zoom;
    const overflowX = imageWidth * scale - width; const overflowY = imageHeight * scale - height;
    // Keep the FFmpeg zoompan contract: on/(30*20). `on` is the 30 fps
    // frame index, so a pan advances over 20 seconds and is not normalized
    // to the scene duration.
    const panProgress = Math.min(1, Math.max(0, localMs) / 20000);
    offsetX = camera === "pan-horizontal" ? -overflowX * panProgress : -overflowX / 2;
    offsetY = camera === "pan-vertical" ? -overflowY * panProgress : -overflowY / 2;
  }
  return { scale, offsetX, offsetY };
}
