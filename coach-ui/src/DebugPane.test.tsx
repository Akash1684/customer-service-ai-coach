import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import DebugPane from "./DebugPane";

const mockUseDataChannel = vi.fn();

vi.mock("@livekit/components-react", () => ({
  useDataChannel: (topic: string) => mockUseDataChannel(topic),
}));

function payload(obj: unknown): Uint8Array {
  return new TextEncoder().encode(JSON.stringify(obj));
}

describe("DebugPane", () => {
  beforeEach(() => {
    mockUseDataChannel.mockReset();
  });

  it("shows a waiting message when no heartbeats have arrived", () => {
    mockUseDataChannel.mockReturnValue({ message: undefined });
    render(<DebugPane />);
    expect(screen.getByText(/Waiting for agent/i)).toBeInTheDocument();
  });

  it("subscribes to the liveness topic", () => {
    mockUseDataChannel.mockReturnValue({ message: undefined });
    render(<DebugPane />);
    expect(mockUseDataChannel).toHaveBeenCalledWith("liveness");
  });

  it("renders incoming heartbeats newest-first", async () => {
    mockUseDataChannel.mockReturnValue({
      message: { payload: payload({ seq: 1, t_ms: 0, status: "alive" }) },
    });
    const { rerender } = render(<DebugPane />);

    await act(async () => {
      mockUseDataChannel.mockReturnValue({
        message: { payload: payload({ seq: 2, t_ms: 2000, status: "alive" }) },
      });
      rerender(<DebugPane />);
    });

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent(/seq\s*2/);
    expect(items[1]).toHaveTextContent(/seq\s*1/);
  });

  it("ignores malformed liveness payloads without crashing", () => {
    mockUseDataChannel.mockReturnValue({
      message: { payload: new Uint8Array([0xff, 0xff, 0xff]) },
    });
    render(<DebugPane />);
    // Should still show the waiting state since nothing parsed.
    expect(screen.getByText(/Waiting for agent/i)).toBeInTheDocument();
  });
});
