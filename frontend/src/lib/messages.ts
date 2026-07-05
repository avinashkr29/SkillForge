import type { BBox } from "./geometry";

export type SessionState =
  | "IDLE"
  | "LISTENING"
  | "PARSING_COMMAND"
  | "SEARCHING"
  | "NEEDS_SELECTION"
  | "LOCKED"
  | "TRACKING"
  | "TEMPORARILY_LOST"
  | "LOST"
  | "STOPPED"
  | "ERROR";

export type ParsedCommand = {
  intent: "track_object" | "stop_tracking" | "unclear";
  object_phrase: string | null;
  base_object: string | null;
  attributes: {
    color: string | null;
    size: string | null;
    material: string | null;
    position: string | null;
  };
  action_context: string | null;
  requires_confirmation: boolean;
  reason: string;
};

export type DetectionResult = {
  detection_id: string;
  label: string;
  confidence: number;
  bbox: BBox;
  mask: unknown | null;
  prompt_version: number;
};

export type TargetState = {
  target_id: string;
  tracker_id: number;
  label: string;
  bbox: BBox;
  confidence: number;
  status: "SEARCHING" | "LOCKED" | "TRACKING" | "TEMPORARILY_LOST" | "LOST";
  last_seen_ts: string;
  lost_frames: number;
};

export type Metrics = {
  video_fps: number;
  yoloe_inference_latency_ms: number;
  context_verification_latency_ms: number;
  speech_transcription_latency_ms: number;
  command_parsing_latency_ms: number;
  transcript_to_first_detection_ms: number;
  tracking_update_latency_ms: number;
  id_switches: number;
  lost_and_reacquired_count: number;
};

export type WsEnvelope = {
  type: string;
  ts: string;
  frame_id?: number;
  payload: Record<string, unknown>;
};

export type LegoVerificationResponse = {
  verified_colors: string[];
  mode: string;
  reason: string;
  latency_ms: number;
};

export function backendHttpUrl(): string {
  return import.meta.env.VITE_BACKEND_HTTP_URL ?? "http://localhost:8000";
}

export function backendWsUrl(): string {
  if (import.meta.env.VITE_BACKEND_WS_URL) {
    return import.meta.env.VITE_BACKEND_WS_URL;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.hostname || "localhost"}:8000/ws/teaching`;
}
