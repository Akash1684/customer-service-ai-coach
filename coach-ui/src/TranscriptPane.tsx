import { useDataChannel } from "@livekit/components-react";
import { useEffect, useState } from "react";

import {
  applyTranscriptPacket,
  EMPTY_TRANSCRIPT_STATE,
  parseTranscriptPacket,
  TRANSCRIPT_TOPIC,
  type TranscriptState,
} from "./transcript";

/**
 * Transcript pane — renders finalized segments as a crisp list, and shows
 * the current in-flight Whisper partial as a faded/italic "draft" line
 * underneath so the user gets immediate feedback while speaking. A small
 * "● Listening…" badge pulses whenever a partial is active.
 */
export default function TranscriptPane() {
  const [state, setState] = useState<TranscriptState>(EMPTY_TRANSCRIPT_STATE);
  const { message } = useDataChannel(TRANSCRIPT_TOPIC);

  useEffect(() => {
    if (!message) return;
    const packet = parseTranscriptPacket(message.payload);
    if (!packet) return;
    setState((prev) => applyTranscriptPacket(prev, packet));
  }, [message]);

  const hasFinals = state.finals.length > 0;
  const isListening = state.partial.length > 0;
  const showEmptyHint = !hasFinals && !isListening;

  return (
    <section
      aria-label="Live transcript"
      style={{
        marginTop: "1.5rem",
        padding: "1rem",
        borderRadius: "8px",
        background: "rgba(255,255,255,0.04)",
        maxWidth: "520px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.5rem",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "1rem", opacity: 0.8 }}>Live transcript</h2>
        {isListening && (
          <span
            data-testid="transcript-listening"
            style={{
              fontSize: "0.75rem",
              padding: "0.15rem 0.5rem",
              borderRadius: "999px",
              background: "rgba(159, 176, 209, 0.15)",
              color: "#9fb0d1",
              animation: "pulse 1.4s ease-in-out infinite",
            }}
          >
            ● Listening…
          </span>
        )}
      </div>
      {showEmptyHint && (
        <p style={{ opacity: 0.6 }}>
          Speak into your microphone — text will appear here as you talk.
        </p>
      )}
      {hasFinals && (
        <div style={{ fontSize: "0.95rem", lineHeight: 1.5 }}>
          {state.finals.map((seg, i) => (
            <p
              key={i}
              style={{ margin: "0.25rem 0", color: "#e6ebf5" }}
              data-testid="transcript-final"
            >
              {seg}
            </p>
          ))}
        </div>
      )}
      {isListening && (
        <p
          data-testid="transcript-partial"
          style={{
            margin: "0.5rem 0 0",
            fontSize: "0.95rem",
            lineHeight: 1.5,
            fontStyle: "italic",
            color: "#9fb0d1",
            opacity: 0.85,
          }}
        >
          {state.partial}
        </p>
      )}
      <style>{"@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.45} }"}</style>
    </section>
  );
}
