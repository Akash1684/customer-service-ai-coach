/**
 * Pure helpers for the `transcript` data-channel topic.
 *
 * The agent publishes JSON payloads of shape `{ text: string, is_final: boolean }`
 * every time Whisper emits a (partial or final) transcript. The UI renders
 * the latest partial in one spot and accumulates finals into a scrolling list.
 */

export const TRANSCRIPT_TOPIC = "transcript";

export interface TranscriptPacket {
  text: string;
  is_final: boolean;
}

export interface TranscriptState {
  /** Current in-flight partial transcript (not yet finalized). */
  partial: string;
  /** Finalized transcript segments, oldest-first. */
  finals: string[];
}

export const EMPTY_TRANSCRIPT_STATE: TranscriptState = { partial: "", finals: [] };

/** Maximum number of final segments retained for display. */
export const MAX_FINAL_SEGMENTS = 20;

/** Parse a raw data-channel payload. Returns null if it doesn't match the shape. */
export function parseTranscriptPacket(payload: Uint8Array): TranscriptPacket | null {
  try {
    const text = new TextDecoder().decode(payload);
    const json = JSON.parse(text) as unknown;
    if (!isTranscriptPacket(json)) return null;
    return json;
  } catch {
    return null;
  }
}

/**
 * Apply a transcript packet to the rolling state.
 * - Non-final packets replace `partial`.
 * - Final packets flush `partial` into `finals` (capped at MAX_FINAL_SEGMENTS).
 */
export function applyTranscriptPacket(
  prev: TranscriptState,
  packet: TranscriptPacket,
): TranscriptState {
  const trimmed = packet.text.trim();
  if (!trimmed) return prev;

  if (packet.is_final) {
    const nextFinals = [...prev.finals, trimmed].slice(-MAX_FINAL_SEGMENTS);
    return { partial: "", finals: nextFinals };
  }
  return { ...prev, partial: trimmed };
}

function isTranscriptPacket(value: unknown): value is TranscriptPacket {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  return typeof obj.text === "string" && typeof obj.is_final === "boolean";
}
