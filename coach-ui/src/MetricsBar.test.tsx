import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import MetricsBar from "./MetricsBar";
import type { MetricsSnapshot } from "./metrics";

const mockUseDataChannel = vi.fn();

vi.mock("@livekit/components-react", () => ({
  useDataChannel: (topic: string) => mockUseDataChannel(topic),
}));

function payload(obj: unknown): Uint8Array {
  return new TextEncoder().encode(JSON.stringify(obj));
}

function snap(overrides: Partial<MetricsSnapshot> = {}): MetricsSnapshot {
  return {
    t_ms: 1_000,
    fillers_total: 0,
    fillers_last: null,
    prohibited_hits: 0,
    prohibited_last: null,
    sentiment_tag: "Neutral",
    sentiment_score: 0,
    ...overrides,
  };
}

describe("MetricsBar", () => {
  beforeEach(() => {
    mockUseDataChannel.mockReset();
  });

  it("subscribes to the metrics topic", () => {
    mockUseDataChannel.mockReturnValue({ message: undefined });
    render(<MetricsBar />);
    expect(mockUseDataChannel).toHaveBeenCalledWith("metrics");
  });

  it("renders the three metric tiles with empty-state placeholders", () => {
    mockUseDataChannel.mockReturnValue({ message: undefined });
    render(<MetricsBar />);
    expect(screen.getByTestId("metric-fillers")).toHaveTextContent("0");
    expect(screen.getByTestId("metric-prohibited")).toHaveTextContent("0");
    expect(screen.getByTestId("metric-sentiment")).toHaveTextContent("Neutral");
  });

  it("reflects incoming snapshot values", () => {
    mockUseDataChannel.mockReturnValue({
      message: {
        payload: payload(
          snap({
            fillers_total: 4,
            fillers_last: "um",
            prohibited_hits: 1,
            prohibited_last: "calm down",
            sentiment_tag: "Negative",
            sentiment_score: -0.42,
          }),
        ),
      },
    });
    render(<MetricsBar />);
    expect(screen.getByTestId("metric-fillers")).toHaveTextContent("4");
    expect(screen.getByTestId("metric-fillers")).toHaveTextContent("um");
    expect(screen.getByTestId("metric-prohibited")).toHaveTextContent("1");
    expect(screen.getByTestId("metric-prohibited")).toHaveTextContent("calm down");
    expect(screen.getByTestId("metric-sentiment")).toHaveTextContent("Negative");
  });

  it("ignores malformed payloads", () => {
    mockUseDataChannel.mockReturnValue({
      message: { payload: new Uint8Array([0xff, 0xfe]) },
    });
    render(<MetricsBar />);
    // Falls back to the empty state.
    expect(screen.getByTestId("metric-fillers")).toHaveTextContent("0");
  });
});
