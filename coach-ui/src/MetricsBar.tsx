import { useDataChannel } from "@livekit/components-react";
import { useEffect, useState } from "react";

import {
  EMPTY_METRICS,
  METRICS_TOPIC,
  parseMetricsPacket,
  type MetricsSnapshot,
  type SentimentTag,
} from "./metrics";

/**
 * MetricsBar — live coaching counters above the transcript.
 *
 * Subscribes to the `metrics` topic and renders three tiles: fillers,
 * prohibited-phrase hits, and sentiment pill. Snapshots are
 * state-replacement, so we just cache the latest packet.
 */
export default function MetricsBar() {
  const [snap, setSnap] = useState<MetricsSnapshot>(EMPTY_METRICS);
  const { message } = useDataChannel(METRICS_TOPIC);

  useEffect(() => {
    if (!message) return;
    const parsed = parseMetricsPacket(message.payload);
    if (parsed) setSnap(parsed);
  }, [message]);

  return (
    <section
      aria-label="Coaching metrics"
      data-testid="metrics-bar"
      style={{
        marginTop: "1rem",
        padding: "0.75rem",
        borderRadius: "8px",
        background: "rgba(255,255,255,0.04)",
        display: "grid",
        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
        gap: "0.75rem",
      }}
    >
      <Tile
        label="Fillers"
        value={String(snap.fillers_total)}
        sub={snap.fillers_last ? `"${snap.fillers_last}"` : "—"}
        testId="metric-fillers"
      />
      <Tile
        label="Prohibited"
        value={String(snap.prohibited_hits)}
        sub={snap.prohibited_last ? `"${snap.prohibited_last}"` : "—"}
        accent={snap.prohibited_hits > 0 ? "#ff8888" : undefined}
        testId="metric-prohibited"
      />
      <Tile
        label="Sentiment"
        value={snap.sentiment_tag}
        sub={snap.sentiment_score !== 0 ? snap.sentiment_score.toFixed(2) : "—"}
        accent={sentimentAccent(snap.sentiment_tag)}
        testId="metric-sentiment"
      />
    </section>
  );
}

interface TileProps {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
  testId?: string;
}

function Tile({ label, value, sub, accent, testId }: TileProps) {
  return (
    <div
      data-testid={testId}
      style={{
        padding: "0.5rem 0.75rem",
        borderRadius: "6px",
        background: "rgba(255,255,255,0.03)",
        minHeight: "3.5rem",
      }}
    >
      <div style={{ fontSize: "0.7rem", opacity: 0.6, textTransform: "uppercase", letterSpacing: "0.5px" }}>
        {label}
      </div>
      <div
        style={{
          fontSize: "1.25rem",
          fontWeight: 600,
          color: accent ?? "#e6ebf5",
          marginTop: "0.15rem",
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: "0.75rem", opacity: 0.6, marginTop: "0.1rem" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function sentimentAccent(tag: SentimentTag): string | undefined {
  if (tag === "Positive") return "#66d68f";
  if (tag === "Negative") return "#ff8888";
  return undefined;
}
