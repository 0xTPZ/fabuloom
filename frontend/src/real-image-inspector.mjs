/**
 * Browser-safe pixel evidence for the Visual Inspector V1.2.
 *
 * This module deliberately does not know character names, defect labels or
 * asset filenames. It consumes decoded RGBA pixels and optional broad
 * composition regions. Results are visual evidence, not an artistic verdict.
 */

export const REAL_IMAGE_INSPECTION_FORMAT = "fabuloom.real-image-inspection/0.1";

const finite = (value) => typeof value === "number" && Number.isFinite(value);

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function normalizeRegion(region, width, height) {
  const source = region || { left: 0, top: 0, right: width, bottom: height };
  const left = clamp(Math.floor(Number(source.left) || 0), 0, width);
  const top = clamp(Math.floor(Number(source.top) || 0), 0, height);
  const right = clamp(Math.ceil(Number(source.right) || width), left, width);
  const bottom = clamp(Math.ceil(Number(source.bottom) || height), top, height);
  return { left, top, right, bottom, width: right - left, height: bottom - top };
}

function luminance(r, g, b) {
  return (0.2126 * r) + (0.7152 * g) + (0.0722 * b);
}

function colorDistance(first, second) {
  return Math.sqrt(
    ((first[0] - second[0]) ** 2) +
    ((first[1] - second[1]) ** 2) +
    ((first[2] - second[2]) ** 2),
  );
}

function sampleBackground(image, region) {
  const points = [
    [region.left + 2, region.top + 2],
    [Math.max(region.left + 2, region.right - 3), region.top + 2],
    [region.left + 2, Math.max(region.top + 2, region.bottom - 3)],
    [Math.max(region.left + 2, region.right - 3), Math.max(region.top + 2, region.bottom - 3)],
  ];
  const colors = points.map(([x, y]) => {
    const index = (y * image.width + x) * 4;
    return [image.rgba[index], image.rgba[index + 1], image.rgba[index + 2]];
  });
  return [
    Math.round(colors.reduce((sum, color) => sum + color[0], 0) / colors.length),
    Math.round(colors.reduce((sum, color) => sum + color[1], 0) / colors.length),
    Math.round(colors.reduce((sum, color) => sum + color[2], 0) / colors.length),
  ];
}

function boundsForPixels(points) {
  if (!points.length) return null;
  let left = points[0].x;
  let top = points[0].y;
  let right = points[0].x;
  let bottom = points[0].y;
  for (const point of points) {
    left = Math.min(left, point.x);
    top = Math.min(top, point.y);
    right = Math.max(right, point.x);
    bottom = Math.max(bottom, point.y);
  }
  right += 1;
  bottom += 1;
  return { left, top, right, bottom, width: right - left, height: bottom - top };
}

function unionBounds(boundsList) {
  const values = boundsList.filter(Boolean);
  if (!values.length) return null;
  const left = Math.min(...values.map((bounds) => bounds.left));
  const top = Math.min(...values.map((bounds) => bounds.top));
  const right = Math.max(...values.map((bounds) => bounds.right));
  const bottom = Math.max(...values.map((bounds) => bounds.bottom));
  return { left, top, right, bottom, width: right - left, height: bottom - top };
}

function boundsGap(first, second) {
  const horizontal = Math.max(first.left - second.right, second.left - first.right, 0);
  const vertical = Math.max(first.top - second.bottom, second.top - first.bottom, 0);
  return Math.hypot(horizontal, vertical);
}

function buildForegroundMask(image, region, background, options) {
  const mask = new Uint8Array(image.width * image.height);
  const alphaThreshold = Number(options.alphaThreshold ?? 16);
  const colorTolerance = Number(options.colorTolerance ?? 28);
  const luminanceFloor = Number(options.luminanceFloor ?? 42);
  let selected = 0;
  for (let y = region.top; y < region.bottom; y += 1) {
    for (let x = region.left; x < region.right; x += 1) {
      const index = (y * image.width + x) * 4;
      const alpha = image.rgba[index + 3];
      if (alpha < alphaThreshold) continue;
      const color = [image.rgba[index], image.rgba[index + 1], image.rgba[index + 2]];
      const selectedPixel = colorDistance(color, background) >= colorTolerance || luminance(...color) >= luminanceFloor;
      if (selectedPixel) {
        mask[y * image.width + x] = 1;
        selected += 1;
      }
    }
  }
  return { mask, selected };
}

function connectedComponents(mask, width, height, region, minArea) {
  const visited = new Uint8Array(mask.length);
  const components = [];
  const neighbors = [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]];
  for (let y = region.top; y < region.bottom; y += 1) {
    for (let x = region.left; x < region.right; x += 1) {
      const startIndex = y * width + x;
      if (!mask[startIndex] || visited[startIndex]) continue;
      const queue = [[x, y]];
      visited[startIndex] = 1;
      const points = [];
      while (queue.length) {
        const [currentX, currentY] = queue.pop();
        points.push({ x: currentX, y: currentY });
        for (const [offsetX, offsetY] of neighbors) {
          const nextX = currentX + offsetX;
          const nextY = currentY + offsetY;
          if (nextX < region.left || nextX >= region.right || nextY < region.top || nextY >= region.bottom) continue;
          const nextIndex = nextY * width + nextX;
          if (!mask[nextIndex] || visited[nextIndex]) continue;
          visited[nextIndex] = 1;
          queue.push([nextX, nextY]);
        }
      }
      if (points.length < minArea) continue;
      const bounds = boundsForPixels(points);
      components.push({
        area: points.length,
        bounds,
        centroid: {
          x: points.reduce((sum, point) => sum + point.x, 0) / points.length,
          y: points.reduce((sum, point) => sum + point.y, 0) / points.length,
        },
      });
    }
  }
  return components.sort((first, second) => second.area - first.area);
}

function ratio(value, total) {
  return total > 0 ? value / total : 0;
}

function regionFromBounds(bounds, x0, y0, x1, y1) {
  if (!bounds) return null;
  return {
    left: bounds.left + bounds.width * x0,
    top: bounds.top + bounds.height * y0,
    right: bounds.left + bounds.width * x1,
    bottom: bounds.top + bounds.height * y1,
    width: bounds.width * (x1 - x0),
    height: bounds.height * (y1 - y0),
  };
}

function maskStats(mask, image, region) {
  let selected = 0;
  let edgePixels = 0;
  for (let y = region.top; y < region.bottom; y += 1) {
    for (let x = region.left; x < region.right; x += 1) {
      const index = y * image.width + x;
      if (mask[index]) {
        selected += 1;
        const neighbor = mask[index - 1] || mask[index + 1] || mask[index - image.width] || mask[index + image.width];
        if (!neighbor) edgePixels += 1;
      }
    }
  }
  return {
    selected,
    area: region.width * region.height,
    occupancy: ratio(selected, region.width * region.height),
    edgeDensity: ratio(edgePixels, selected),
  };
}

function issue({ code, severity = "hypothesis", confidence = "low", message, region = null, evidence = {} }) {
  return { code, severity, confidence, origin: "visual-pixels", message, region, evidence };
}

function compareRegion(reference, current, region, options = {}) {
  const colorTolerance = Number(options.colorTolerance ?? 12);
  const alphaTolerance = Number(options.alphaTolerance ?? 8);
  const left = Math.max(0, Math.floor(region.left));
  const top = Math.max(0, Math.floor(region.top));
  const right = Math.min(current.width, Math.ceil(region.right));
  const bottom = Math.min(current.height, Math.ceil(region.bottom));
  let differingPixels = 0;
  let totalPixels = 0;
  for (let y = top; y < bottom; y += 1) {
    for (let x = left; x < right; x += 1) {
      const index = (y * current.width + x) * 4;
      const dr = Math.abs(reference.rgba[index] - current.rgba[index]);
      const dg = Math.abs(reference.rgba[index + 1] - current.rgba[index + 1]);
      const db = Math.abs(reference.rgba[index + 2] - current.rgba[index + 2]);
      const da = Math.abs(reference.rgba[index + 3] - current.rgba[index + 3]);
      if (Math.max(dr, dg, db) > colorTolerance || da > alphaTolerance) differingPixels += 1;
      totalPixels += 1;
    }
  }
  return { bounds: { left, top, right, bottom, width: right - left, height: bottom - top }, differingPixels, totalPixels, differenceRatio: ratio(differingPixels, totalPixels) };
}

export function analyzeRenderedPixels(image, options = {}) {
  if (!image || !Number.isInteger(image.width) || !Number.isInteger(image.height) || !image.rgba || image.rgba.length !== image.width * image.height * 4) {
    throw new TypeError("image must contain width, height and RGBA pixels");
  }
  const region = normalizeRegion(options.region, image.width, image.height);
  const background = options.backgroundColor || sampleBackground(image, region);
  const { mask, selected } = buildForegroundMask(image, region, background, options);
  const components = connectedComponents(mask, image.width, image.height, region, Number(options.minComponentArea ?? 24));
  const foregroundBounds = unionBounds(components.slice(0, Number(options.maxComponents ?? 24)).map((component) => component.bounds));
  const alphaPixels = { transparent: 0, translucent: 0, opaque: 0 };
  for (let index = 3; index < image.rgba.length; index += 4) {
    const alpha = image.rgba[index];
    if (alpha === 0) alphaPixels.transparent += 1;
    else if (alpha < 255) alphaPixels.translucent += 1;
    else alphaPixels.opaque += 1;
  }
  const regionDefinitions = foregroundBounds ? {
    face: regionFromBounds(foregroundBounds, 0.25, 0, 0.75, 0.27),
    torso: regionFromBounds(foregroundBounds, 0.18, 0.22, 0.82, 0.76),
    leftSide: regionFromBounds(foregroundBounds, 0, 0.18, 0.32, 0.72),
    rightSide: regionFromBounds(foregroundBounds, 0.68, 0.18, 1, 0.72),
    feet: regionFromBounds(foregroundBounds, 0.15, 0.72, 0.85, 1),
  } : {};
  const regionMetrics = Object.fromEntries(Object.entries(regionDefinitions).map(([name, bounds]) => [name, { bounds, ...maskStats(mask, image, normalizeRegion(bounds, image.width, image.height)) }]));
  const hasTransparency = alphaPixels.transparent + alphaPixels.translucent > 0;
  const confidence = foregroundBounds && selected > 0 ? (hasTransparency ? "high" : "medium") : "low";
  return {
    format: REAL_IMAGE_INSPECTION_FORMAT,
    dimensions: { width: image.width, height: image.height },
    analysisRegion: region,
    backgroundColor: background,
    alpha: {
      transparentPixels: alphaPixels.transparent,
      translucentPixels: alphaPixels.translucent,
      opaquePixels: alphaPixels.opaque,
      transparentRatio: ratio(alphaPixels.transparent, image.width * image.height),
      hasTransparency,
    },
    foreground: {
      selectedPixels: selected,
      occupancy: ratio(selected, region.width * region.height),
      bounds: foregroundBounds,
      confidence,
      componentCount: components.length,
      components: components.slice(0, 32),
      maskEdgeDensity: maskStats(mask, image, region).edgeDensity,
    },
    regions: regionMetrics,
    limitations: [
      hasTransparency ? "alpha-mask-available" : "opaque-composition-foreground-segmentation-is-heuristic",
      "broad-composition-regions-are-not-rig-landmarks",
      "pixel-evidence-does-not-decide-artistic-approval",
    ],
  };
}

export function compareRenderedPixels(reference, current, options = {}) {
  if (!reference || !current || reference.width !== current.width || reference.height !== current.height) {
    return { compatible: false, differenceRatio: null, regions: {}, reason: "image dimensions differ or image is missing" };
  }
  const region = normalizeRegion(options.region, current.width, current.height);
  const regions = options.regions || {
    full: region,
    face: { left: region.left, top: region.top, right: region.right, bottom: region.top + region.height * 0.34 },
    facialEyes: { left: region.left + region.width * 0.28, top: region.top, right: region.left + region.width * 0.72, bottom: region.top + region.height * 0.16 },
    facialGlasses: { left: region.left + region.width * 0.20, top: region.top + region.height * 0.02, right: region.left + region.width * 0.80, bottom: region.top + region.height * 0.21 },
    facialMouth: { left: region.left + region.width * 0.30, top: region.top + region.height * 0.16, right: region.left + region.width * 0.70, bottom: region.top + region.height * 0.29 },
    facialBeard: { left: region.left + region.width * 0.22, top: region.top + region.height * 0.15, right: region.left + region.width * 0.78, bottom: region.top + region.height * 0.34 },
    lowerBody: { left: region.left, top: region.top + region.height * 0.34, right: region.right, bottom: region.bottom },
  };
  const results = Object.fromEntries(Object.entries(regions).map(([name, bounds]) => [name, compareRegion(reference, current, normalizeRegion(bounds, current.width, current.height), options)]));
  return {
    compatible: true,
    differenceRatio: results.full.differenceRatio,
    regions: results,
    region,
    thresholds: { colorTolerance: Number(options.colorTolerance ?? 12), alphaTolerance: Number(options.alphaTolerance ?? 8) },
  };
}

export function diagnoseRenderedImage(current, { reference = null, referenceMetrics = null, options = {} } = {}) {
  const metrics = analyzeRenderedPixels(current, options);
  const issues = [];
  if (!metrics.foreground.bounds) {
    issues.push(issue({ code: "insufficient-pixel-evidence", severity: "hypothesis", confidence: "low", message: "A composição não permitiu separar uma silhueta confiável do fundo.", evidence: { analysisRegion: metrics.analysisRegion } }));
  }
  const mainComponent = metrics.foreground.components[0];
  const detachedComponents = mainComponent ? metrics.foreground.components.slice(1).filter((component) => component.area >= Math.max(32, mainComponent.area * 0.01) && boundsGap(mainComponent.bounds, component.bounds) >= 10) : [];
  if (detachedComponents.length) {
    issues.push(issue({ code: "disconnected-component", confidence: "low", message: "Foi observado um componente visual relevante separado da silhueta dominante; em uma composição opaca isso é uma hipótese e pode ser um elemento de cenário.", region: unionBounds([mainComponent.bounds, ...detachedComponents.map((component) => component.bounds)]), evidence: { detachedCount: detachedComponents.length, componentAreas: detachedComponents.map((component) => component.area) } }));
  }
  let comparison = null;
  if (reference) {
    comparison = compareRenderedPixels(reference, current, options);
    if (comparison.compatible && comparison.regions.face.differenceRatio >= Number(options.faceDifferenceThreshold ?? 0.22)) {
      issues.push(issue({ code: "facial-region-difference", confidence: "low", message: "A região facial difere da referência visual; a causa pode ser arte, pose ou composição duplicada e exige revisão humana.", region: comparison.regions.face, evidence: { differenceRatio: comparison.regions.face.differenceRatio, referenceKind: "blind-reference" } }));
    }
    if (comparison.compatible) {
      const featureThreshold = Number(options.facialFeatureDifferenceThreshold ?? 0.20);
      for (const feature of ["facialEyes", "facialGlasses", "facialMouth", "facialBeard"]) {
        const featureResult = comparison.regions[feature];
        if (!featureResult || featureResult.differenceRatio < featureThreshold) continue;
        issues.push(issue({ code: "facial-feature-difference", confidence: "low", message: `A região facial ampla (${feature}) difere da referência; pixels isolados não permitem afirmar duplicação ou deslocamento.`, region: featureResult, evidence: { feature, differenceRatio: featureResult.differenceRatio, referenceKind: "blind-reference" } }));
      }
    }
    const currentBounds = metrics.foreground.bounds;
    const referenceBounds = referenceMetrics?.foreground?.bounds;
    if (currentBounds && referenceBounds) {
      const widthRatio = currentBounds.width / Math.max(1, referenceBounds.width);
      const heightRatio = currentBounds.height / Math.max(1, referenceBounds.height);
      const scaleDelta = Math.max(Math.abs(widthRatio - 1), Math.abs(heightRatio - 1));
      if (scaleDelta >= Number(options.scaleDifferenceThreshold ?? 0.18)) {
        issues.push(issue({ code: "silhouette-scale-difference", confidence: "low", message: "A silhueta ocupa uma escala diferente da referência; o resultado pode ser intencional e não é um defeito confirmado.", region: currentBounds, evidence: { widthRatio, heightRatio, scaleDelta, referenceBounds, currentBounds } }));
      }
    }
    const currentComponents = metrics.foreground.componentCount;
    const referenceComponents = referenceMetrics?.foreground?.componentCount;
    if (finite(referenceComponents) && Math.abs(currentComponents - referenceComponents) >= Number(options.componentDifferenceThreshold ?? 8)) {
      issues.push(issue({ code: "silhouette-component-difference", confidence: "low", message: "A quantidade de componentes visuais relevantes difere da referência; a evidência não distingue articulação real de composição artística.", region: metrics.foreground.bounds, evidence: { currentComponents, referenceComponents } }));
    }
  }
  return {
    format: REAL_IMAGE_INSPECTION_FORMAT,
    metrics,
    comparison,
    issues,
    review: { required: true, state: issues.length ? "human-review-required" : "no-visual-hypothesis", evidenceState: metrics.alpha.hasTransparency ? "alpha-mask-available" : "opaque-composition-heuristic", note: "A análise de pixels produz evidência e hipóteses; aprovação artística e identificação causal permanecem humanas. Composição opaca não confirma juntas ocultas por alpha." },
  };
}

export function combineVisualDiagnostics({ geometry = [], visual = [], ai = [] } = {}) {
  const normalize = (finding, origin) => ({ ...finding, origin: finding.origin || origin });
  const issues = [
    ...geometry.map((finding) => normalize(finding, "geometry")),
    ...visual.map((finding) => normalize(finding, "visual-pixels")),
    ...ai.map((finding) => normalize(finding, "multimodal-ai")),
  ];
  const confirmed = issues.filter((finding) => finding.severity === "error" && finding.confidence === "high").length;
  return {
    issues,
    summary: {
      confirmed,
      warnings: issues.filter((finding) => finding.severity === "warning").length,
      hypotheses: issues.filter((finding) => finding.severity === "hypothesis").length,
      sources: { geometry: geometry.length, visual: visual.length, ai: ai.length },
    },
    review: { required: issues.length > 0 || ai.length > 0, state: issues.length ? "human-review-required" : "no-verified-issues" },
  };
}
