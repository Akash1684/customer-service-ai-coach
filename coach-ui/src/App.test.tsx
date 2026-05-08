import { render, screen, waitFor } from "@testing-library/react";
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

// Mock the token minter so tests don't call jose.
vi.mock("./token", () => ({
  mintToken: vi.fn().mockResolvedValue("fake-minted-jwt"),
}));

describe("App", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders the product title", async () => {
    vi.stubEnv("VITE_LIVEKIT_URL", "ws://127.0.0.1:7880");
    render(<App />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /Customer Service AI Coach/i,
    );
  });

  it("mounts LiveKitRoom once the token has been minted", async () => {
    vi.stubEnv("VITE_LIVEKIT_URL", "ws://127.0.0.1:7880");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId("livekit-room")).toBeInTheDocument();
    });
    expect(screen.getByTestId("room-audio-renderer")).toBeInTheDocument();
  });

  it("shows configuration help when VITE_LIVEKIT_URL is missing", () => {
    vi.stubEnv("VITE_LIVEKIT_URL", "");
    render(<App />);
    expect(screen.getByText(/Missing/i)).toBeInTheDocument();
    expect(screen.queryByTestId("livekit-room")).not.toBeInTheDocument();
  });
});
