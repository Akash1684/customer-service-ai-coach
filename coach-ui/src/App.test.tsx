import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import App from "./App";

// Stub @livekit/components-react so we don't need a real LiveKit connection
// in unit tests.
vi.mock("@livekit/components-react", () => ({
  LiveKitRoom: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="livekit-room">{children}</div>
  ),
  RoomAudioRenderer: () => <div data-testid="room-audio-renderer" />,
  useDataChannel: () => ({ message: undefined }),
}));

vi.mock("@livekit/components-styles", () => ({}));

describe("App", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders the product title", () => {
    vi.stubEnv("VITE_LIVEKIT_URL", "ws://127.0.0.1:7880");
    vi.stubEnv("VITE_LIVEKIT_TOKEN", "fake-jwt");
    render(<App />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /Customer Service AI Coach/i,
    );
  });

  it("mounts LiveKitRoom when env is configured", () => {
    vi.stubEnv("VITE_LIVEKIT_URL", "ws://127.0.0.1:7880");
    vi.stubEnv("VITE_LIVEKIT_TOKEN", "fake-jwt");
    render(<App />);
    expect(screen.getByTestId("livekit-room")).toBeInTheDocument();
    expect(screen.getByTestId("room-audio-renderer")).toBeInTheDocument();
  });

  it("shows configuration help when VITE_LIVEKIT_TOKEN is missing", () => {
    vi.stubEnv("VITE_LIVEKIT_URL", "ws://127.0.0.1:7880");
    vi.stubEnv("VITE_LIVEKIT_TOKEN", "");
    render(<App />);
    expect(screen.getByText(/Missing/i)).toBeInTheDocument();
    expect(screen.queryByTestId("livekit-room")).not.toBeInTheDocument();
  });
});
