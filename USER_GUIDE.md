# User guide

## Dashboard

The dashboard summarizes the local checkout and identifies which capabilities are present. “Local”, “browser”, “CLI” and “partial” labels are intentional status indicators, not promises of a complete production pipeline.

## Projects

**Projetos → ＋ Novo projeto** creates a persistent project under the configured workspace. Open any card with **Abrir produção** to continue it. The app does not upload project files: imported assets, project JSON, narration WAVs and exports stay local.

## Script

The script view edits the active project. **Salvar roteiro** splits sentences into ordered scenes. Saving a changed script does not synthesize audio automatically; use **Áudio → Gerar narração Santa** when the script is ready.

## Narrators

Santa V5 is the approved production reference for this branch. Dora and Alex are visible for integration inspection but are marked as awaiting artistic approval. Older packs and experiments remain in DEV only.

## Audio and preview

After successful generation, the project receives a measured manifest and WAV segments. The browser can play that timeline and drive RMS-based mouth states. Word, phoneme and viseme alignment is not available. If Kokoro, its model, or the voice is unavailable, the Audio card reports the failure and the project remains intact.

## Export

The Exportação view starts an asynchronous local FFmpeg job. Every scene must have an imported image and the project must have generated narration. Progress, failure and the resulting MP4 link are shown in the same view.

## DEV area

DEV pages are diagnostic and experimental. Their presence does not mean that their packs, labs or visual states are Alpha-supported features.
