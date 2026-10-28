/** TypeScript contracts for the visual stage boundary. */

export interface StageAudioSegment {
  id: string;
  text: string;
  voice_id: string;
  language: string;
  audio_uri: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  metadata: Record<string, unknown>;
}

export interface StageAudioManifest {
  id: string;
  timeline_id: string;
  duration_ms: number;
  segments: StageAudioSegment[];
  metadata: Record<string, unknown>;
}

export type PlaybackState = "stopped" | "playing" | "paused" | "ended" | "error";

export interface PlaybackSnapshot {
  state: PlaybackState;
  position_ms: number;
  duration_ms: number;
  active_segment_id: string | null;
  amplitude: number;
}

export interface CharacterPose {
  breathing: number;
  head_rotation: number;
  eye_open: number;
  mouth_open: number;
}

export interface CharacterNode {
  id: string;
  children: CharacterNode[];
}

export interface CharacterRigContract {
  readonly root: CharacterNode;
  update(time_ms: number, is_playing: boolean): void;
  set_speech_amplitude(amplitude: number): void;
  pose(): CharacterPose;
}
