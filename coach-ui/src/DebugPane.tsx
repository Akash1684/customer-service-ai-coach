import { useDataChannel } from "@livekit/components-react";
import { useEffect, useState } from "react";

import {
  LIVENESS_TOPIC,
  addHeartbeat,
  parseHeartbeat,
  type Heartbeat,
} from "./liveness";

/**
 * Debug pane — shows the last 5 liveness heartbeats from the Python agent.
 *
 * Step 2 deliverable: proves the agent→UI data channel works. Later steps
 * replace this with the real MetricsBar, NudgeStream, and TranscriptPane.
 */
export default function DebugPane() {
  const [beats, setBeats] = useState<Heartbeat[]>([]);
  const { message } = useDataChannel(LIVENESS_TOPIC);

  useEffect(() => {
    if (!message) return;
    const hb = parseHeartbeat(message.payload);
    if (!hb) return;
    setBeats((prev) => addHeartbeat(prev, hb));
  }, [message]);

  return (
    <section
      aria-label="Agent liveness debug pane"
      style={{
        marginTop: "1.5rem",
        padding: "1rem",
        borderRadius: "8px",
        background: "rgba(255,255,255,0.04)",
        maxWidth: "520px",
      }}
    >
      <h2 style={{ margin: 0, fontSize: "1rem", opacity: 0.8 }}>
        Agent liveness (last 5 heartbeats)
      </h2>
      {beats.length === 0 ? (
        <p style={{ opacity: 0.6, marginTop: "0.5rem" }}>
          Waiting for agent. Start it with <code>uv run src/coach_agent/main.py dev</code>.
        </p>
      ) : (
        <ul
          style={{
            listStyle: "none",
            padding: 0,
            marginTop: "0.5rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.25rem",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: "0.9rem",
          }}
        >
          {beats.map((b) => (
            <li key={b.seq}>
              seq <strong>{b.seq}</strong> · t={b.t_ms}ms · {b.status}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
