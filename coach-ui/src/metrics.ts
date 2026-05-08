/**
 * Pure helpers for the `metrics` data-channel topic.
 *
 * The agent publishes a `MetricsSnapshot` JSON packet roughly every 250 ms
 * during active speech. The UI keeps only the latest value; metrics are a
 * state-replacement topic, not an append-only stream.
 */

export const METRICS_TOPIC = "metrics";

export type SentimentTag = "Positive" | "Neutral" | "Negative";

export interface MetricsSnapshot {
  t_ms: number;
  fillers_total: number;
  fillers_last: string | null;
  prohibited_hits: number;
  prohibited_last: string | null;
  sentiment_tag: SentimentTag;
  sentiment_score: number;
}

export const EMPTY_METRICS: MetricsSnapshot = {
  t_ms: 0,
  fillers_total: 0,
  fillers_last: null,
  prohibited_hits: 0,
  prohibited_last: null,
  sentiment_tag: "Neutral",
  sentiment_score: 0,
};

/** Parse a raw data-channel payload; returns null if it doesn't match the shape. */
export function parseMetricsPacket(payload: Uint8Array): MetricsSnapshot | null {
  try {
    const json = JSON.parse(new TextDecoder().decode(payload)) as unknown;
    if (!isMetricsSnapshot(json)) return null;
    return json;
  } catch {
    return null;
  }
}

function isSentimentTag(v: unknown): v is SentimentTag {
  return v === "Positive" || v === "Neutral" || v === "Negative";
}

function isMetricsSnapshot(v: unknown): v is MetricsSnapshot {
  if (typeof v !== "object" || v === null) return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.t_ms === "number" &&
    typeof o.fillers_total === "number" &&
    (o.fillers_last === null || typeof o.fillers_last === "string") &&
    typeof o.prohibited_hits === "number" &&
    (o.prohibited_last === null || typeof o.prohibited_last === "string") &&
    isSentimentTag(o.sentiment_tag) &&
    typeof o.sentiment_score === "number"
  );
}
