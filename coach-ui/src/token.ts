/**
 * In-browser LiveKit token minter.
 *
 * Why this exists:
 *   The previous setup used a long-lived static token with a fixed
 *   `identity` claim (`rep-local`). When the page refreshed, LiveKit
 *   rejected the new connection because the old participant with the
 *   same identity was still being cleaned up. Result: refresh = dead UI.
 *
 * What this does:
 *   Mints a short-lived (2 h) JWT on every page load, with a random
 *   identity suffix so refreshes always get a unique participant name
 *   and never collide with their predecessor.
 *
 * Security note:
 *   The `devkey` / `secret` credentials are the well-known
 *   `livekit-server --dev` defaults. Exposing them in a local-only
 *   browser bundle is fine for dev; do not ship this pattern to
 *   production.
 */

import { SignJWT } from "jose";

const API_KEY = (import.meta.env.VITE_LIVEKIT_API_KEY as string | undefined) ?? "devkey";
const API_SECRET = (import.meta.env.VITE_LIVEKIT_API_SECRET as string | undefined) ?? "secret";
const ROOM = (import.meta.env.VITE_LIVEKIT_ROOM as string | undefined) ?? "coach-room";

function randomIdentity(): string {
  const suffix = Math.random().toString(36).slice(2, 10);
  return `rep-${suffix}`;
}

/**
 * Mint a fresh LiveKit access token bound to a unique participant
 * identity. Returns the signed JWT; pass it to `<LiveKitRoom token=…>`.
 */
export async function mintToken(): Promise<string> {
  const identity = randomIdentity();
  const secretBytes = new TextEncoder().encode(API_SECRET);

  return await new SignJWT({
    video: {
      room: ROOM,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
    },
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setIssuer(API_KEY)
    .setSubject(identity)
    .setJti(identity)
    .setExpirationTime("2h")
    .sign(secretBytes);
}
