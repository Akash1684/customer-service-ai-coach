/**
 * App — Step 1 scaffold.
 *
 * For now this is a bare landing page that proves the Vite + React + TS toolchain
 * is wired correctly. Step 2 will introduce <LiveKitRoom> connection + data-channel
 * liveness echo; Step 3 adds the transcript pane; and so on per docs/planning/implementation/plan.md.
 */
export default function App() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        background: "#0b1020",
        color: "#e6ebf5",
      }}
    >
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <h1 style={{ margin: 0, fontSize: "2rem" }}>Customer Service AI Coach — v0</h1>
        <p style={{ marginTop: "0.75rem", opacity: 0.75 }}>
          Step 1 scaffold. Real-time audio, transcripts, metrics, and coaching nudges
          land in subsequent steps per{" "}
          <code>docs/planning/implementation/plan.md</code>.
        </p>
      </div>
    </main>
  );
}
