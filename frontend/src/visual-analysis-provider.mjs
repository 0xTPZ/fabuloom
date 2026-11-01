/** Provider-neutral contract for optional multimodal visual review. */

export const VISUAL_ANALYSIS_PROVIDER_FORMAT = "fabuloom.visual-analysis-provider/0.1";

export function createVisualAnalysisRequest({ image = null, artisticReference = null, suspiciousRegions = [], geometryDiagnostics = [], animationContext = null } = {}) {
  return {
    format: VISUAL_ANALYSIS_PROVIDER_FORMAT,
    image,
    artisticReference,
    suspiciousRegions,
    geometryDiagnostics,
    animationContext,
  };
}

export function validateVisualAnalysisProvider(provider) {
  if (!provider || typeof provider.analyzeImage !== "function" || typeof provider.analyzeSequence !== "function" || typeof provider.capabilities !== "function" || typeof provider.providerMetadata !== "function") {
    throw new TypeError("VisualAnalysisProvider must expose analyzeImage, analyzeSequence, capabilities and providerMetadata");
  }
  return provider;
}

export function createUnavailableVisualAnalysisProvider({ reason = "Nenhum provedor multimodal foi configurado para esta execução." } = {}) {
  const metadata = Object.freeze({
    id: "unavailable",
    name: "No visual analysis provider",
    version: "0.1",
    available: false,
    network: false,
    reason,
  });
  const capabilities = Object.freeze({ image: false, sequence: false, regions: false, geometryContext: false });
  const provider = {
    providerMetadata: () => metadata,
    capabilities: () => capabilities,
    async analyzeImage(request) {
      return { status: "not-executed", provider: metadata, requestFormat: request?.format || VISUAL_ANALYSIS_PROVIDER_FORMAT, suggestions: [], humanReviewRequired: true, reason };
    },
    async analyzeSequence(request) {
      return { status: "not-executed", provider: metadata, requestFormat: request?.format || VISUAL_ANALYSIS_PROVIDER_FORMAT, suggestions: [], humanReviewRequired: true, reason };
    },
  };
  return validateVisualAnalysisProvider(provider);
}
