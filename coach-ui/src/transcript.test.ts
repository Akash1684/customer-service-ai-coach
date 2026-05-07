import { describe, it, expect } from "vitest";

import {
  applyTranscriptPacket,
  EMPTY_TRANSCRIPT_STATE,
  MAX_FINAL_SEGMENTS,
  parseTranscriptPacket,
  type TranscriptState,
} from "./transcript";

function encode(obj: unknown): Uint8Array {
  return new TextEncoder().encode(JSON.stringify(obj));
}

describe("parseTranscriptPacket", () => {
  it("parses a valid partial packet", () => {
    expect(parseTranscriptPacket(encode({ text: "hello", is_final: false }))).toEqual({
      text: "hello",
      is_final: false,
    });
  });

  it("parses a valid final packet", () => {
    expect(parseTranscriptPacket(encode({ text: "hi there", is_final: true }))).toEqual({
      text: "hi there",
      is_final: true,
    });
  });

  it("returns null for garbage bytes", () => {
    expect(parseTranscriptPacket(new Uint8Array([0xff, 0xfe, 0xfd]))).toBeNull();
  });

  it("returns null when `is_final` is missing", () => {
    expect(parseTranscriptPacket(encode({ text: "oops" }))).toBeNull();
  });

  it("returns null when `text` is not a string", () => {
    expect(parseTranscriptPacket(encode({ text: 42, is_final: true }))).toBeNull();
  });
});

describe("applyTranscriptPacket", () => {
  it("updates partial transcript on non-final packet", () => {
    const out = applyTranscriptPacket(EMPTY_TRANSCRIPT_STATE, {
      text: "hello world",
      is_final: false,
    });
    expect(out.partial).toBe("hello world");
    expect(out.finals).toEqual([]);
  });

  it("replaces partial when a new non-final arrives", () => {
    const s1 = applyTranscriptPacket(EMPTY_TRANSCRIPT_STATE, {
      text: "hel",
      is_final: false,
    });
    const s2 = applyTranscriptPacket(s1, { text: "hello", is_final: false });
    expect(s2.partial).toBe("hello");
  });

  it("flushes partial into finals on a final packet", () => {
    const s1 = applyTranscriptPacket(EMPTY_TRANSCRIPT_STATE, {
      text: "hello there",
      is_final: false,
    });
    const s2 = applyTranscriptPacket(s1, { text: "hello there friend", is_final: true });
    expect(s2.partial).toBe("");
    expect(s2.finals).toEqual(["hello there friend"]);
  });

  it("ignores empty / whitespace-only packets", () => {
    const s1 = applyTranscriptPacket(EMPTY_TRANSCRIPT_STATE, { text: "   ", is_final: false });
    expect(s1).toBe(EMPTY_TRANSCRIPT_STATE);
    const s2 = applyTranscriptPacket(EMPTY_TRANSCRIPT_STATE, { text: "", is_final: true });
    expect(s2).toBe(EMPTY_TRANSCRIPT_STATE);
  });

  it(`caps finals at ${MAX_FINAL_SEGMENTS} entries, dropping oldest`, () => {
    let state: TranscriptState = EMPTY_TRANSCRIPT_STATE;
    for (let i = 0; i < MAX_FINAL_SEGMENTS + 3; i++) {
      state = applyTranscriptPacket(state, { text: `seg-${i}`, is_final: true });
    }
    expect(state.finals).toHaveLength(MAX_FINAL_SEGMENTS);
    expect(state.finals[0]).toBe("seg-3"); // oldest 3 were dropped
    expect(state.finals[state.finals.length - 1]).toBe(`seg-${MAX_FINAL_SEGMENTS + 2}`);
  });

  it("trims text edges", () => {
    const s = applyTranscriptPacket(EMPTY_TRANSCRIPT_STATE, {
      text: "  hello  ",
      is_final: true,
    });
    expect(s.finals).toEqual(["hello"]);
  });
});
