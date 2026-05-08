import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import "@livekit/components-styles";

import MetricsBar from "./MetricsBar";
import TranscriptPane from "./TranscriptPane";

/**
 * App — mounts a LiveKit room that publishes the rep's mic, and renders
 * the two live panes: MetricsBar (coaching counters) and TranscriptPane
 * (partial + final transcripts from the agent's Whisper STT).
 */
export default function App() {
  const url = import.meta.env.VITE_LIVEKIT_URL as string | undefined;
  const token = import.meta.env.VITE_LIVEKIT_TOKEN as string | undefined;

  if (!url || !token) {
    return (
      <main style={pageStyle}>
        <div style={cardStyle}>
          <h1 style={{ margin: 0 }}>Customer Service AI Coach</h1>
          <p style={{ marginTop: "1rem" }}>
            Missing <code>VITE_LIVEKIT_URL</code> or <code>VITE_LIVEKIT_TOKEN</code>.
          </p>
          <p style={{ opacity: 0.7 }}>
            Copy <code>.env.local.example</code> to <code>.env.local</code> and generate a dev
            token with <code>lk token create --api-key devkey --api-secret secret --join --room
            coach-room --identity rep-local --valid-for 720h --token-only</code>.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      <div style={cardStyle}>
        <h1 style={{ margin: 0 }}>Customer Service AI Coach</h1>
        <p style={{ marginTop: "0.5rem", opacity: 0.7 }}>
          Speak into your mic. The agent transcribes with <code>faster-whisper</code> and
          runs live coaching detectors.
        </p>
        <LiveKitRoom
          token={token}
          serverUrl={url}
          audio={true}
          video={false}
          connect={true}
          connectOptions={{ autoSubscribe: true }}
          onError={(e) => console.error("LiveKit connection error:", e)}
        >
          <RoomAudioRenderer />
          <MetricsBar />
          <TranscriptPane />
        </LiveKitRoom>
      </div>
    </main>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  display: "grid",
  placeItems: "center",
  fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
  background: "#0b1020",
  color: "#e6ebf5",
  padding: "2rem",
};

const cardStyle: React.CSSProperties = {
  padding: "2rem",
  borderRadius: "12px",
  background: "rgba(255,255,255,0.03)",
  maxWidth: "720px",
  width: "100%",
  boxShadow: "0 1px 2px rgba(0,0,0,0.4), inset 0 0 0 1px rgba(255,255,255,0.06)",
};
