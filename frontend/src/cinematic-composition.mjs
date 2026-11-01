/** Shared camera contract used by the browser composition preview.
 * FFmpeg consumes the same persisted fields (camera, duration_ms and image).
 * The browser keeps the calculation pure so it can be regression-tested.
 */
export function resolveCinematicTransform({ camera = "static", progress = 0, width, height, imageWidth, imageHeight, localMs = 0 }) {
  const baseScale = Math.max(width / imageWidth, height / imageHeight);
  let scale = baseScale; let offsetX = (width - imageWidth * scale) / 2; let offsetY = (height - imageHeight * scale) / 2;
  if (camera !== "static") {
    const zoom = camera === "zoom" ? 1 + Math.min(0.12, localMs / 1000 * 0.0015 * 30) : 1.08;
    scale *= zoom;
    const overflowX = imageWidth * scale - width; const overflowY = imageHeight * scale - height;
    offsetX = camera === "pan-horizontal" ? -overflowX * Math.min(1, progress / 0.6) : -overflowX / 2;
    offsetY = camera === "pan-vertical" ? -overflowY * Math.min(1, progress / 0.6) : -overflowY / 2;
  }
  return { scale, offsetX, offsetY };
}
