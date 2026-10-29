import { captureSantaV3Frames, SantaV3Rig, SantaV3SceneRenderer } from "./santa-v3-engine.ts";
import { SANTA_V4_PACK } from "./santa-v4-pack.mjs";

/**
 * Santa V4 reuses the deterministic V3 scene choreography and changes only
 * the illustrated character pack. This keeps the art refinement isolated
 * from the animation, audio, and frame-capture contracts.
 */
export class SantaV4Rig extends SantaV3Rig {}

export class SantaV4SceneRenderer extends SantaV3SceneRenderer {
  constructor(canvas, rig = new SantaV4Rig(), options = {}) {
    super(canvas, rig, {
      ...options,
      pack: SANTA_V4_PACK,
      title: "SANTA V4  ·  TOPAZIOVERSE",
    });
  }
}

export { captureSantaV3Frames, SANTA_V4_PACK };
