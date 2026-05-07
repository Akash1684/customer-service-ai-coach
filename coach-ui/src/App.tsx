import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import "@livekit/components-styles";

import DebugPane from "./DebugPane";

/**
 * App — Step 2 scaffold.
 *
 * Wraps the app in a LiveKitRoom, publishes the rep's microphone, and mounts
 * the DebugPane which displays incoming liveness heartbeats from the Python
 * agent. Step 3 will swap the DebugPane for a real TranscriptPane; Steps 4+
 * layer in scripts, metrics, nudges, and the download flow.
 */
export default function App() {
  const url = import.meta.env.VITE_LIVEKIT_URL as string | undefined;
  const token = import.meta.env.VITE_LIVEKIT_TOKEN as string | undefined;

  if (!url || !token) {
    return (
      <main style={pageStyle}>
        <div style={cardStyle}>
          <h1 style={{ margin: 0 }}>Customer Service AI Coach — v0</h1>
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
        <h1 style={{ margin: 0 }}>Customer Service AI Coach — v0</h1>
        <p style={{ marginTop: "0.5rem", opacity: 0.7 }}>
          Step 2 scaffold. Mic publishes into the local LiveKit room; the agent echoes liveness
          heartbeats below.
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
          <DebugPane />
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
  maxWidth: "640px",
  width: "100%",
  boxShadow: "0 1px 2px rgba(0,0,0,0.4), inset 0 0 0 1px rgba(255,255,255,0.06)",
};
