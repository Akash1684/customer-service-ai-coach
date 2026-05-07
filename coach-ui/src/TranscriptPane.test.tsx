import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import TranscriptPane from "./TranscriptPane";

const mockUseDataChannel = vi.fn();

vi.mock("@livekit/components-react", () => ({
  useDataChannel: (topic: string) => mockUseDataChannel(topic),
}));

function payload(obj: unknown): Uint8Array {
  return new TextEncoder().encode(JSON.stringify(obj));
}

describe("TranscriptPane", () => {
  beforeEach(() => {
    mockUseDataChannel.mockReset();
  });

  it("subscribes to the transcript topic", () => {
    mockUseDataChannel.mockReturnValue({ message: undefined });
    render(<TranscriptPane />);
    expect(mockUseDataChannel).toHaveBeenCalledWith("transcript");
  });

  it("shows the empty state when nothing has arrived", () => {
    mockUseDataChannel.mockReturnValue({ message: undefined });
    render(<TranscriptPane />);
    expect(screen.getByText(/Speak into your microphone/i)).toBeInTheDocument();
  });

  it("renders partial text as a draft line alongside the Listening indicator", () => {
    mockUseDataChannel.mockReturnValue({
      message: { payload: payload({ text: "hello", is_final: false }) },
    });
    render(<TranscriptPane />);
    // Partial text is visible (italic draft) and the Listening badge pulses.
    expect(screen.getByTestId("transcript-partial")).toHaveTextContent("hello");
    expect(screen.getByTestId("transcript-listening")).toBeInTheDocument();
  });

  it("renders a final transcript and hides the Listening indicator", async () => {
    mockUseDataChannel.mockReturnValue({
      message: { payload: payload({ text: "hi", is_final: false }) },
    });
    const { rerender } = render(<TranscriptPane />);
    expect(screen.getByTestId("transcript-listening")).toBeInTheDocument();

    await act(async () => {
      mockUseDataChannel.mockReturnValue({
        message: { payload: payload({ text: "hi there friend", is_final: true }) },
      });
      rerender(<TranscriptPane />);
    });

    expect(screen.queryByTestId("transcript-listening")).not.toBeInTheDocument();
    expect(screen.getByTestId("transcript-final")).toHaveTextContent("hi there friend");
  });
});
