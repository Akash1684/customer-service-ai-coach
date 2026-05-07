import { describe, it, expect } from "vitest";

import {
  EMPTY_METRICS,
  parseMetricsPacket,
  type MetricsSnapshot,
} from "./metrics";

function encode(obj: unknown): Uint8Array {
  return new TextEncoder().encode(JSON.stringify(obj));
}

const VALID: MetricsSnapshot = {
  t_ms: 123,
  fillers_total: 3,
  fillers_last: "um",
  wpm_current: 145,
  wpm_avg: 152,
  pacing_band: "ok",
  prohibited_hits: 1,
  prohibited_last: "calm down",
  sentiment_tag: "Neutral",
  sentiment_score: 0.12,
};

describe("parseMetricsPacket", () => {
  it("parses a valid snapshot", () => {
    expect(parseMetricsPacket(encode(VALID))).toEqual(VALID);
  });

  it("accepts null strings for fillers_last / prohibited_last", () => {
    const snap = { ...VALID, fillers_last: null, prohibited_last: null };
    expect(parseMetricsPacket(encode(snap))).toEqual(snap);
  });

  it("returns null when pacing_band is invalid", () => {
    const snap = { ...VALID, pacing_band: "lightspeed" };
    expect(parseMetricsPacket(encode(snap))).toBeNull();
  });

  it("returns null when sentiment_tag is invalid", () => {
    const snap = { ...VALID, sentiment_tag: "Joyful" };
    expect(parseMetricsPacket(encode(snap))).toBeNull();
  });

  it("returns null when a numeric field is missing", () => {
    const { wpm_avg: _unused, ...rest } = VALID;
    expect(parseMetricsPacket(encode(rest))).toBeNull();
  });

  it("returns null for garbage bytes", () => {
    expect(parseMetricsPacket(new Uint8Array([0xff, 0xfe]))).toBeNull();
  });
});

describe("EMPTY_METRICS", () => {
  it("is a valid snapshot shape", () => {
    expect(parseMetricsPacket(encode(EMPTY_METRICS))).toEqual(EMPTY_METRICS);
  });
});
