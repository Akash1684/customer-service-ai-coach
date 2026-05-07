# Research: Frontend — React + Vite + `@livekit/components-react`

**Scope:** Minimal React + Vite frontend that connects to the local LiveKit room, publishes the rep's mic, subscribes to `nudges` / `metrics` data channels, renders the script + nudge stream + counters + live transcript, and offers a client-side markdown download.

**Date:** 2026-05-07

---

## 1. Why Vite over Next.js

LiveKit publishes an official **Next.js** starter (`agent-starter-react` which uses Next.js under the hood for App Router + server actions), but for our constraints:

| | Next.js | **Vite** (chosen) |
|---|---|---|
| Need SSR? | Useful for production | **No** — local-only SPA |
| Need a server-side token endpoint? | Yes, app router loves this | **No** — static dev token in `.env.local` |
| Bundle size / startup time | Larger | ~3× smaller |
| Boilerplate | Heavier | Minimal |

Vite gives us `pnpm dev` → hot-reload in ~100 ms with no routing or server-side rendering noise. Perfect for a single-page local coach UI.

---

## 2. Package layout

```
coach-ui/
├── .env.local
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── components/
    │   ├── ScriptPanel.tsx
    │   ├── MetricsBar.tsx
    │   ├── NudgeStream.tsx
    │   ├── TranscriptPane.tsx
    │   └── DownloadButton.tsx
    ├── hooks/
    │   └── useCoachSession.ts
    └── types.ts
```

Dependencies (`package.json`):

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "livekit-client": "^2.x",
    "@livekit/components-react": "^2.x",
    "@livekit/components-styles": "^1.x"
  },
  "devDependencies": {
    "vite": "^5.x",
    "@vitejs/plugin-react": "^4.x",
    "typescript": "^5.x",
    "@types/react": "^18.x",
    "@types/react-dom": "^18.x"
  }
}
```

---

## 3. LiveKit connection

### Static dev token

Per Q13 / P0-lean, the frontend uses a long-lived dev token issued once via the LiveKit CLI:

```bash
lk token create \
  --api-key devkey --api-secret secret \
  --join --room coach-room \
  --identity rep-local \
  --valid-for 720h \
  > dev-token.txt
```

Then in `coach-ui/.env.local`:

```
VITE_LIVEKIT_URL=ws://127.0.0.1:7880
VITE_LIVEKIT_TOKEN=<contents of dev-token.txt>
VITE_LIVEKIT_ROOM=coach-room
```

### `App.tsx` skeleton

```tsx
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import "@livekit/components-styles";
import CoachUI from "./components/CoachUI";

export default function App() {
  const url = import.meta.env.VITE_LIVEKIT_URL!;
  const token = import.meta.env.VITE_LIVEKIT_TOKEN!;
  return (
    <LiveKitRoom
      token={token}
      serverUrl={url}
      connect={true}
      audio={true}
      video={false}
      connectOptions={{ autoSubscribe: true }}
    >
      <RoomAudioRenderer />
      <CoachUI />
    </LiveKitRoom>
  );
}
```

`RoomAudioRenderer` is a no-op for us (no bot audio) but it's standard hygiene.

---

## 4. Receiving data channels from the agent

The `@livekit/components-react` hook `useDataChannel(topic)` gives us message streams:

```tsx
import { useDataChannel } from "@livekit/components-react";
import { useEffect, useState } from "react";

export function useMetrics() {
  const { message } = useDataChannel("metrics");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  useEffect(() => {
    if (!message) return;
    const text = new TextDecoder().decode(message.payload);
    setMetrics(JSON.parse(text));
  }, [message]);
  return metrics;
}

export function useNudges() {
  const { message } = useDataChannel("nudges");
  const [nudges, setNudges] = useState<Nudge[]>([]);
  useEffect(() => {
    if (!message) return;
    const text = new TextDecoder().decode(message.payload);
    setNudges((prev) => [...prev, JSON.parse(text)]);
  }, [message]);
  return nudges;
}
```

Each nudge payload is `{ id, t_ms, text_markdown, event_type }`. Metrics payload is the shape documented in `detectors.md` §8.

---

## 5. Sending commands to the agent

Via RPC. `@livekit/components-react` exposes `useRoomContext()` → `room.localParticipant.performRpc(...)`.

```tsx
const room = useRoomContext();
async function startSession(scriptId: string) {
  await room.localParticipant.performRpc({
    destinationIdentity: "coach-agent",
    method: "start_session",
    payload: JSON.stringify({ script_id: scriptId }),
  });
}

async function updateSettings(patch: Partial<Settings>) {
  await room.localParticipant.performRpc({
    destinationIdentity: "coach-agent",
    method: "update_settings",
    payload: JSON.stringify(patch),
  });
}
```

The agent registers matching RPC handlers:

```python
@ctx.room.local_participant.register_rpc_method("start_session")
async def start_session(data): ...
@ctx.room.local_participant.register_rpc_method("stop_session")
async def stop_session(data): ...
@ctx.room.local_participant.register_rpc_method("update_settings")
async def update_settings(data): ...
```

---

## 6. UI structure (P0)

### Single-screen layout

```
┌─────────────────────────────────────────────────────┐
│  Header: script selector · Start / Stop · Download  │
├─────────────────────────┬───────────────────────────┤
│                         │  Live metrics bar         │
│  ScriptPanel            │  fillers  WPM  dead-air   │
│  (speaker-turn          │  prohibited  sentiment    │
│   with visible          ├───────────────────────────┤
│   customer lines,       │  Nudge stream             │
│   rep lines             │  (markdown nudges         │
│   highlighted)          │   newest on top or        │
│                         │   bottom-sticky)          │
│                         ├───────────────────────────┤
│                         │  Live transcript pane     │
│                         │  (partial + final)        │
├─────────────────────────┴───────────────────────────┤
│  Settings (inline accordion): dead-air threshold,   │
│  prohibited-phrase list, pacing band                │
└─────────────────────────────────────────────────────┘
```

### Component responsibilities

- **ScriptPanel** — displays the selected script as alternating `[Customer]` / `[Rep]` blocks; rep lines visually prominent. Not auto-scrolling — rep reads at their own pace.
- **MetricsBar** — live counters + a small sentiment pill. Uses `useMetrics()`.
- **NudgeStream** — virtualized list of markdown nudges (newest at top sticky). Uses `useNudges()`. Markdown rendered with a tiny renderer (`marked` or `react-markdown` — `marked` is lighter).
- **TranscriptPane** — shows the rep's partial and final transcript with ~3 second rolling window plus a "Show full" toggle.
- **DownloadButton** — on click, serializes in-browser state to a markdown string (see §7) and triggers a `Blob` download. No server roundtrip.

---

## 7. Download button (client-side only)

```tsx
function buildMarkdown(state: SessionState): string {
  return [
    `# Customer Service AI Coach — Session Report`,
    ``,
    `**Script:** ${state.scriptTitle}`,
    `**Duration:** ${fmtDuration(state.durationMs)}`,
    ``,
    `## Metrics`,
    `- Fillers: ${state.metrics.fillers_total}`,
    `- Avg WPM: ${state.metrics.wpm_avg}`,
    `- Dead air: ${state.metrics.dead_air_count} events (${state.metrics.dead_air_total_s}s total)`,
    `- Prohibited-phrase hits: ${state.metrics.prohibited_hits}`,
    `- Sentiment profile: ${state.sentimentProfile}`,
    ``,
    `## Event timeline`,
    ...state.events.map(e => `- [${fmtTime(e.t_ms)}] ${e.type} — ${e.detail}`),
    ``,
    `## Coaching nudges`,
    ...state.nudges.map(n => `- [${fmtTime(n.t_ms)}] ${n.text_markdown}`),
    ``,
    `## Narrative summary`,
    state.narrativeSummary || "(not generated)",
    `## Full transcript`,
    state.fullTranscript,
  ].join("\n");
}

function download(state) {
  const md = buildMarkdown(state);
  const blob = new Blob([md], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `coach-session-${new Date().toISOString()}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}
```

The **narrative summary** is requested from the agent on `stop_session`; the agent runs the end-of-session LLM call and pushes the markdown via a final `nudges` packet tagged `{ event_type: "final_summary" }`. The UI holds it until download.

---

## 8. Microphone permissions and publish

`@livekit/components-react`'s `LiveKitRoom` with `audio={true}` handles mic permission and publishing automatically. Two caveats for P0:

- **Echo cancellation / noise suppression** — we enable browser defaults (`echoCancellation: true, noiseSuppression: true`) on the audio constraints. LiveKit's default audio capture options already do this.
- **No audio-output track from agent** — since the agent doesn't speak, there's nothing to play. `RoomAudioRenderer` stays mounted but silent.

---

## 9. Open items for the design phase

- **Settings persistence.** Per Q13/Q8 P0 has no storage; settings reset on refresh. UI holds them in React state for the session. `localStorage` is zero-cost and would make UX slightly better — pending a 1-line call on design.
- **Session start/stop UX polish.** Confirm modal on stop? For P0: no, just stop and enable download. Can add in design.
- **Script picker** — three scripts in P0 (per Q11), so a simple dropdown is fine.

---

## 10. References

- `@livekit/components-react` — <https://docs.livekit.io/reference/components/react/>
- `livekit-client` — <https://docs.livekit.io/reference/client-sdk-js/>
- Vite — <https://vitejs.dev>
- LiveKit React starter (heavier, Next.js; for reference only) — <https://github.com/livekit-examples/agent-starter-react>
- LiveKit CLI `token create` — <https://docs.livekit.io/reference/developer-tools/livekit-cli/>
- `useDataChannel` and friends — <https://docs.livekit.io/reference/components/react/hook/usedatachannel/>
- RPC — <https://docs.livekit.io/transport/data/rpc/>
