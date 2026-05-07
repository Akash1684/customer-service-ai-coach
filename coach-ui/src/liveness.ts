/**
 * Pure helpers for decoding liveness data packets.
 *
 * Kept dependency-free so tests can exercise them without pulling in the
 * LiveKit runtime or DOM APIs. The React component consumes these via
 * `useDataChannel`, but the logic lives here so it is exercisable in
 * isolation.
 */

export type LivenessStatus = "alive";

/** Data-channel topic used by the agent and UI for liveness heartbeats. */
export const LIVENESS_TOPIC = "liveness";

export interface Heartbeat {
  seq: number;
  t_ms: number;
  status: LivenessStatus;
}

/** Maximum number of heartbeats retained for the DebugPane display. */
export const MAX_HEARTBEATS = 5;

/**
 * Parse a raw liveness data-packet payload. Returns `null` if the bytes are
 * not valid JSON or do not match the expected shape.
 */
export function parseHeartbeat(payload: Uint8Array): Heartbeat | null {
  try {
    const text = new TextDecoder().decode(payload);
    const json = JSON.parse(text) as unknown;
    if (!isValidHeartbeat(json)) return null;
    return json;
  } catch {
    return null;
  }
}

/**
 * Push a new heartbeat onto the (newest-first) list, capped at
 * `MAX_HEARTBEATS` entries. Returns a new array.
 */
export function addHeartbeat(prev: Heartbeat[], hb: Heartbeat): Heartbeat[] {
  return [hb, ...prev].slice(0, MAX_HEARTBEATS);
}

function isValidHeartbeat(value: unknown): value is Heartbeat {
  if (typeof value !== "object" || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.seq === "number" &&
    Number.isInteger(obj.seq) &&
    obj.seq >= 0 &&
    typeof obj.t_ms === "number" &&
    obj.t_ms >= 0 &&
    obj.status === "alive"
  );
}
