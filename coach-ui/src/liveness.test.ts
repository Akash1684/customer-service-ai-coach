import { describe, it, expect } from "vitest";

import { addHeartbeat, parseHeartbeat, MAX_HEARTBEATS, type Heartbeat } from "./liveness";

function encode(obj: unknown): Uint8Array {
  return new TextEncoder().encode(JSON.stringify(obj));
}

describe("parseHeartbeat", () => {
  it("parses a valid heartbeat payload", () => {
    const hb = parseHeartbeat(encode({ seq: 3, t_ms: 5000, status: "alive" }));
    expect(hb).toEqual({ seq: 3, t_ms: 5000, status: "alive" });
  });

  it("returns null for non-JSON bytes", () => {
    expect(parseHeartbeat(new Uint8Array([0xff, 0xff, 0xff]))).toBeNull();
  });

  it("returns null when `seq` is missing", () => {
    expect(parseHeartbeat(encode({ t_ms: 100, status: "alive" }))).toBeNull();
  });

  it("returns null when `seq` is negative", () => {
    expect(parseHeartbeat(encode({ seq: -1, t_ms: 100, status: "alive" }))).toBeNull();
  });

  it("returns null when `status` is wrong", () => {
    expect(parseHeartbeat(encode({ seq: 1, t_ms: 0, status: "dead" }))).toBeNull();
  });

  it("returns null for JSON that is not an object", () => {
    expect(parseHeartbeat(encode("not an object"))).toBeNull();
    expect(parseHeartbeat(encode(null))).toBeNull();
    expect(parseHeartbeat(encode([1, 2, 3]))).toBeNull();
  });
});

describe("addHeartbeat", () => {
  const hb = (seq: number, t_ms: number): Heartbeat => ({ seq, t_ms, status: "alive" });

  it("prepends newest heartbeat so list is newest-first", () => {
    const out = addHeartbeat([hb(1, 0)], hb(2, 2000));
    expect(out.map((h) => h.seq)).toEqual([2, 1]);
  });

  it("handles empty list", () => {
    expect(addHeartbeat([], hb(1, 0))).toEqual([hb(1, 0)]);
  });

  it(`caps the list at ${MAX_HEARTBEATS} entries, dropping oldest`, () => {
    let list: Heartbeat[] = [];
    for (let i = 1; i <= MAX_HEARTBEATS + 3; i++) {
      list = addHeartbeat(list, hb(i, i * 100));
    }
    expect(list).toHaveLength(MAX_HEARTBEATS);
    expect(list[0].seq).toBe(MAX_HEARTBEATS + 3); // newest at head
    expect(list[list.length - 1].seq).toBe(4); // oldest retained
  });
});
