# Research: WebRTC / Voice-AI Stack Comparison

**Date:** 2026-05-07

## Recommendation

Use LiveKit server as the SFU and LiveKit Agents SDK as the voice-AI
framework. No other stack evaluated satisfies all four P0 constraints.

## Constraints

P0 requires:

1. Self-hosted. No cloud calls, no API keys to external services.
2. Python agent running STT and VAD. No TTS in the pipeline.
3. Three-terminal dev setup with no Docker.
4. Apache-2.0 or MIT licence.

## Stack layers

Three layers exist. Pion, LiveKit, and Pipecat are not peers.

| Layer | Role | Options |
|---|---|---|
| 1. WebRTC primitives | `PeerConnection`, DTLS, RTP, SCTP | Pion (Go), libwebrtc (C++), aiortc (Python) |
| 2. SFU / media server | Route media, handle signaling and auth | LiveKit server, MediaSoup, Janus, Ion-SFU, Jitsi Videobridge |
| 3. Voice-AI framework | STT / VAD / LLM / TTS pipeline, session lifecycle | LiveKit Agents, Pipecat, Vocode |

LiveKit server at Layer 2 is built on Pion at Layer 1. Pipecat at Layer 3
runs on top of an external Layer 2 SFU (Daily cloud, LiveKit, or
MediaSoup). This project selects at Layer 2 and Layer 3.

## Layer 2 evaluation

| SFU | Language | Licence | Zero-config dev mode | Built-in auth | Python client SDK |
|---|---|---|---|---|---|
| LiveKit | Go | Apache-2.0 | `livekit-server --dev` | JWT, baked `devkey`/`secret` | Yes (`livekit`) |
| MediaSoup | Node | ISC | No signaling, no app shell | No | No |
| Janus | C | GPL-3 | Config file plus plugins | Plugin-specific | No |
| Ion-SFU | Go | MIT | Requires separate ion-sdk | External | Community |
| Jitsi Videobridge | Java | Apache-2.0 | Requires JVM plus Prosody XMPP | Via Jitsi Meet | No |
| Pion (raw) | Go | MIT | Protocol library, not a server | No | No |

LiveKit is the only entry that binds a port, mints a token, and accepts a
browser WebRTC connection without additional code from this project.
MediaSoup requires a Node signaling and auth server that this project
does not need to write when using LiveKit. Janus and Jitsi Videobridge
require additional services. Ion-SFU requires separate server and client
repositories. Pion is a protocol library.

## Layer 3 evaluation

| Framework | Default transport | Licence | No-TTS pipeline |
|---|---|---|---|
| LiveKit Agents | LiveKit WebRTC, native | Apache-2.0 | `AgentSession(tts=None)` is a supported shape |
| Pipecat | Daily (cloud) | BSD-2 | Supported, requires manual pipeline graph construction |
| Vocode | Twilio or WebSocket | MIT | Framework assumes TTS. Removing TTS requires a fork |

Vocode's TTS assumption rules it out. Pipecat supports no-TTS but its
default transport is Daily cloud, not a self-hosted SFU. Running Pipecat
on self-hosted LiveKit adds a second framework's version matrix and
abstractions alongside the SFU.

## Reasoning

LiveKit at both layers wins on four measurable dimensions.

1. **Zero-config dev mode.** `livekit-server --dev` mints tokens and
   binds the SFU port with no config file. The nearest alternative
   (Pipecat plus MediaSoup) adds a Node signaling and auth server
   owned by this project.
2. **Process count.** The LiveKit stack runs three processes
   (`livekit-server`, agent, UI). Pipecat plus MediaSoup runs four
   (MediaSoup, signaling server, Pipecat agent, UI).
3. **Declarative no-TTS shape.** LiveKit Agents accepts
   `AgentSession(stt=..., vad=..., llm=None, tts=None)` in four lines.
   Pipecat requires constructing a pipeline graph object.
4. **Silero VAD wired into session state.** LiveKit Agents emits
   `user_state_changed` events (`speaking` / `listening` / `away`).
   This project uses the `speaking → listening` transition to call
   `stream.flush()`. No custom VAD loop exists in this codebase.

## Trade-offs accepted

1. **Vendor concentration.** Layers 2 and 3 are both LiveKit. The
   licence is Apache-2.0 and the server is in Go, so a fork is viable.
2. **Dev-mode worker dispatch.** Commit `1d676da` records a
   parent-process Whisper pre-warm that broke the forked worker's thread
   state. The fix was reverting the pre-warm.
3. **Codec control.** LiveKit negotiates Opus for audio, which matches
   this audio-only app. MediaSoup fits a video product requiring
   per-track codec tuning.

## References

- LiveKit server: https://github.com/livekit/livekit
- LiveKit Agents (Python): https://github.com/livekit/agents
- Pion WebRTC: https://github.com/pion/webrtc
- Pipecat: https://github.com/pipecat-ai/pipecat
- MediaSoup: https://mediasoup.org
- Janus Gateway: https://github.com/meetecho/janus-gateway
- Ion-SFU: https://github.com/ionorg/ion-sfu
- Jitsi Videobridge: https://github.com/jitsi/jitsi-videobridge
- Vocode: https://github.com/vocodedev/vocode-python
