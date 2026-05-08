# Research: WebRTC / Voice-AI Stack Comparison

**Scope:** Compare LiveKit against the other popular real-time audio stacks we could have built on — **Pion**, **Pipecat**, **MediaSoup**, **Janus**, **Ion-SFU**, **Vocode** — against our specific constraints (fully local, Python-native agent, STT + VAD only, no TTS, fast prototype), and record why **LiveKit** is the recommended choice for both the media-server layer and the voice-AI-framework layer.

**Date:** 2026-05-07

---

## 1. Framing: these options live at different layers

A frequent confusion in this space is lumping Pion, LiveKit, and Pipecat into one list — they're actually at three different layers of the stack:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 3 — Voice-AI framework                                │
│   LiveKit Agents SDK │ Pipecat │ Vocode                     │
│   (STT ↔ VAD ↔ LLM ↔ TTS pipeline, session lifecycle)       │
├─────────────────────────────────────────────────────────────┤
│ Layer 2 — Media server / SFU                                │
│   LiveKit server │ MediaSoup │ Janus │ Ion-SFU │ Jitsi VB   │
│   (routes WebRTC media between participants, signaling)     │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 — WebRTC primitives                                 │
│   Pion (Go) │ libwebrtc (C++) │ aiortc (Python)             │
│   (PeerConnection, DTLS, RTP, SCTP — protocol only)         │
└─────────────────────────────────────────────────────────────┘
```

LiveKit server at Layer 2 is **built on Pion** at Layer 1. Pipecat at Layer 3 does **not** ship a Layer 2 SFU — it plugs into Daily (cloud), WebSocket, or an external LiveKit/Janus for media routing. Comparing "LiveKit vs Pion" is comparing a full SFU to a raw protocol library; comparing "LiveKit vs Pipecat" is comparing an all-in-one stack to a framework that still needs an SFU beneath it.

This document covers both layers. We need Layer 2 and Layer 3, and we prefer one vendor if the fit is right.

---

## 2. Decision criteria (from our P0 constraints)

| Criterion | Why it matters |
|---|---|
| **Fully local / self-hosted** | Core product constraint — no data leaves the laptop. Cloud-only transports are out. |
| **Python-native agent** | Detectors, sentiment, nudges all happen in Python. Agent must be first-class Python, not a wrapper. |
| **STT + VAD only, no TTS** | Coach never talks back. The framework must let us drop the TTS leg of the pipeline cleanly. |
| **One-command dev setup** | Prototype needs to be runnable in 3 terminals. No Docker Compose, no Kubernetes, no cloud keys. |
| **Open source, permissive licence** | No license tax for a local tool. |
| **Active maintenance** | Bus-factor, security patches, docs. |
| **Low LOC burden in our codebase** | The smaller the framework-integration layer we own, the faster we ship. |

---

## 3. Layer 2 comparison — Media server / SFU

| SFU | Language | Licence | Built-in signaling | Dev-mode one-liner | Built-in auth / tokens | Python client SDK | Fit for us |
|---|---|---|---|---|---|---|---|
| **LiveKit** | Go (uses Pion) | Apache-2.0 | ✅ | ✅ `livekit-server --dev` | ✅ JWT, dev key baked in | ✅ (`livekit`) | **Chosen** |
| **MediaSoup** | Node.js (C++ workers) | ISC | ❌ (you write it) | ❌ (you write app shell) | ❌ (BYO) | ❌ (JS only) | Too much custom glue |
| **Janus** | C | GPL-3 | ✅ (plugins) | ⚠️ needs config file | ✅ (plugin-specific) | ❌ | Plugin-in-C friction |
| **Ion-SFU** | Go (uses Pion) | MIT | ⚠️ (separate ion-sfu + ion-sdk) | ⚠️ | ⚠️ | ⚠️ (community) | Lower-level than LiveKit |
| **Jitsi Videobridge** | Java | Apache-2.0 | ✅ (XMPP) | ⚠️ JVM + Prosody XMPP | ✅ (Jitsi Meet) | ⚠️ | Conference-first, not 1:agent |
| **Raw Pion** | Go | MIT | ❌ | N/A | ❌ | ❌ | We'd be writing our own SFU |

**Why LiveKit wins Layer 2:**

- **`livekit-server --dev` is a single binary with a baked-in dev API key.** Literal zero-config for local.
- **First-class Python client SDK** means our agent connects with `rtc.Room()` rather than WebSocket-bridging over `aiortc`.
- **Signaling is built in** (WebSocket + protobuf). MediaSoup leaves signaling to you — we'd write 500+ lines of server/client glue just to reach feature parity with a 3-line LiveKit setup.
- **JWT auth with dev defaults** (`devkey` / `secret`) lets us mint tokens in-browser (see `coach-ui/src/token.ts`) without a separate token service.

**Why not Pion directly:** Pion is excellent — it's what LiveKit is built on — but using it raw means writing our own SFU, signaling, auth, and client SDKs. That's a multi-week project before we can transcribe a single word. Pion is the right choice if you're building LiveKit; it is not the right choice if you want to use it.

**Why not MediaSoup:** Node.js forces either a Node agent (losing our Python detectors) or a WebSocket bridge to Python (adding latency and a failure mode). MediaSoup also ships no built-in signaling or auth — you wire those yourself. Great if you need the flexibility; too heavy for a 1-person prototype.

**Why not Janus:** Plugin architecture is C-native. Adding a new media handler means writing a C plugin and rebuilding Janus. Overkill for "capture one audio track and hand it to Python".

**Why not Ion-SFU:** Pion's own simpler-SFU offering. Smaller community than LiveKit, fewer client SDKs (browser SDK is community-maintained), no integrated voice-agent framework. You'd essentially pick Ion if you wanted a smaller binary, but you'd give up Layer 3 entirely.

---

## 4. Layer 3 comparison — Voice-AI framework

| Framework | Transport options | STT / VAD / LLM / TTS plugins | Can drop the TTS leg? | Python-native agent | License |
|---|---|---|---|---|---|
| **LiveKit Agents** | **LiveKit WebRTC** (native), WebSocket | Whisper (incl. faster-whisper), Silero VAD, OpenAI-compatible LLM (Ollama works), Cartesia/Deepgram TTS | ✅ all four slots optional | ✅ first-class | Apache-2.0 |
| **Pipecat** | Daily (cloud-default), WebSocket, LiveKit, Twilio, FastAPI-WS | Whisper, Deepgram, Cartesia, OpenAI, many more | ✅ pipelines are composable | ✅ | BSD-2 |
| **Vocode** | Twilio, Vonage, WebSocket, FastAPI | Deepgram, AssemblyAI, ElevenLabs, OpenAI | ⚠️ designed around TTS-always | ✅ | MIT |

**Why LiveKit Agents wins Layer 3:**

- **One-vendor story.** LiveKit Agents ships with native LiveKit WebRTC transport — no bridge process, no dual dependency management. Pipecat on LiveKit transport works, but we'd be managing two frameworks' abstractions, their versions, and their bug surfaces.
- **`AgentSession(stt=..., vad=..., llm=None, tts=None)` is legal and natural.** The STT + VAD-only shape is exactly what we need. Pipecat supports this too, but requires you to construct the pipeline graph manually; LiveKit Agents makes it declarative.
- **Silero VAD driving finalization is built in.** We get `user_state_changed` events (`speaking` / `listening` / `away`) out of the box — our detector wiring hooks directly into these without writing a VAD loop.
- **Worker / dispatch model.** `cli.run_app(server)` gives us a worker that auto-joins rooms, forks a subprocess per session, handles lifecycle. We didn't write any of that.

**Why not Pipecat (the closest competitor):**

Pipecat is excellent and probably the most popular open-source voice-AI framework as of 2026. It lost to LiveKit Agents for us because:

1. **Transport defaults are cloud.** Pipecat's documented happy path is Daily (cloud-hosted). Self-hosted local transport (FastAPI-WS or LiveKit) works but is the less-trodden path — less example code, more edge cases.
2. **No built-in SFU.** Pipecat is Layer 3 only. If we pick Pipecat, we still pick Layer 2 separately and plug them together. LiveKit Agents + LiveKit server = one decision.
3. **Pipeline graph is more verbose.** Pipecat's `Pipeline([TransportInput, STT, LLM, TTS, TransportOutput])` is powerful but overkill for our STT + VAD + detectors shape. LiveKit Agents' `AgentSession` is higher-level for the 80% case.
4. **Smaller Silero VAD integration.** Pipecat has Silero support but it's less deeply wired than LiveKit Agents' `user_state_changed` events.

**Why not Vocode:**

- Designed with TTS always enabled (voice-bot first). Forcing no-TTS requires fighting the framework.
- Smaller community than either LiveKit Agents or Pipecat.
- Telephony-first (Twilio/Vonage), not browser-first.

---

## 5. Head-to-head: LiveKit (full stack) vs Pipecat + MediaSoup

Since Pipecat + an external SFU is the most credible alternative path, here's the direct comparison:

| | **LiveKit (Layers 2+3)** | **Pipecat + MediaSoup** |
|---|---|---|
| Processes to run locally | 3 (`livekit-server`, agent, UI) | 3 (mediasoup, pipecat, UI) — **but** mediasoup needs a custom signaling/auth shim written by us |
| Self-hosted dev setup | `brew install livekit && livekit-server --dev` | Build MediaSoup + your own signaling server (Node app) |
| Python agent transport | Native `rtc.Room()` | WebSocket bridge or custom LiveKit transport |
| VAD integration | Built-in (`user_state_changed`) | Manual integration in pipeline |
| Rooms / sessions / dispatch | Built-in | You write it |
| Token / auth | Built-in JWT, dev defaults | You write it |
| Client SDKs | React, Vue, iOS, Android, Flutter, Unity | mediasoup-client JS; others community |
| LOC in our repo to reach parity | ~400 LOC agent + ~200 LOC UI | ~1,500+ LOC (signaling server, auth, room mgmt, reconnect) |
| When to pick the alternative | You need MediaSoup's per-track codec flexibility | — |

---

## 6. Recommendation: **LiveKit** at both layers

We pick **LiveKit server + LiveKit Agents SDK** for this project.

**Reasoning, in priority order:**

1. **Single vendor, single abstraction, single set of docs.** We manage one version matrix (`livekit-server`, `livekit-agents`, `@livekit/components-react`) instead of two or three. For a 1-person prototype this halves the research overhead.

2. **The dev-mode ergonomics are unmatched.** `livekit-server --dev` requires no config file, no JWT endpoint, no Docker — just a binary. The `devkey` / `secret` defaults let us mint tokens in the browser (see `coach-ui/src/token.ts`) for trivial page-refresh safety.

3. **Python Agents is first-class.** The same team ships the server and the Python agent framework. No "Python as an afterthought" — the Python SDK feature-tracks the server.

4. **The STT-only shape fits naturally.** `AgentSession(stt=LocalFasterWhisperSTT(), vad=silero.VAD.load(), llm=None, tts=None)` is 4 lines; the SDK treats the unused slots as no-ops.

5. **Silero VAD drives finalization for free.** The SDK emits `user_state_changed` events — `speaking → listening` is our cue to flush the STT stream. We don't write a VAD loop or heuristics.

6. **Production path is identical.** If we ever move to the cloud, `livekit-server --dev` → LiveKit Cloud (or self-hosted LiveKit in a container) is a config change, not a rewrite. Pipecat + MediaSoup would require replacing more pieces.

7. **Active and well-funded.** LiveKit Inc. (Y Combinator, Series A) ships weekly releases, plugin ecosystem is healthy, issue response is fast.

---

## 7. Trade-offs we accepted by choosing LiveKit

Not writing this up honestly would be marketing, not research.

- **Vendor concentration.** If LiveKit Inc. pivots away from OSS, we depend on a community fork. Mitigation: Apache-2.0 licence, Go codebase, active external contributors — fork-ability is real.
- **Worker dispatch in `dev` mode is sometimes opaque.** We hit this when a parent-process Whisper pre-warm broke the forked worker's thread state (see commit `1d676da`). Pipecat's flatter process model might have avoided it.
- **Less codec flexibility than MediaSoup.** LiveKit picks Opus for audio and negotiates codecs for us. For an audio-only coaching app this is correct; if we ever needed raw H.264 B-frame tuning, MediaSoup wins.
- **More abstractions to learn than Pion.** Small cost given everything we get back.

None of these outweigh the ergonomic and velocity wins for a local, Python-centric, STT-only prototype.

---

## 8. References

- LiveKit server — <https://github.com/livekit/livekit>
- LiveKit Agents (Python) — <https://github.com/livekit/agents>
- Pion WebRTC — <https://github.com/pion/webrtc>
- Pipecat — <https://github.com/pipecat-ai/pipecat>
- MediaSoup — <https://mediasoup.org>
- Janus Gateway — <https://github.com/meetecho/janus-gateway>
- Ion-SFU — <https://github.com/ionorg/ion-sfu>
- Jitsi Videobridge — <https://github.com/jitsi/jitsi-videobridge>
- Vocode — <https://github.com/vocodedev/vocode-python>
