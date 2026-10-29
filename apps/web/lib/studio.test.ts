import { describe, expect, it } from "vitest";

import { LABELS } from "./contract";
import { toRequest, type Prediction } from "./inference";
import type { SketchAction } from "./sketch";
import { canRecognize, INITIAL_STUDIO, studioReducer, type StudioEvent, type StudioState } from "./studio";

const CANVAS = { width: 400, height: 300 };

function run(state: StudioState, ...events: StudioEvent[]): StudioState {
  return events.reduce(studioReducer, state);
}

function sketch(...actions: SketchAction[]): StudioEvent[] {
  return actions.map((action) => ({ type: "sketch", action }));
}

const LINE = sketch(
  { type: "begin", point: [20, 30], width: 8 },
  { type: "extend", points: [[120, 40], [220, 90]] },
  { type: "end" },
);

function prediction(uncertain: boolean): Prediction {
  const scores = uncertain ? [0.5, 0.42, 0.04] : [0.97, 0.02, 0.01];
  const top3 = (["sun", "flower", "cat"] as const).map((label, rank) => ({ label, score: scores[rank] }));
  return { label: "sun", score: scores[0], top3, uncertain, modelVersion: "gap-test", latencyMs: 3 };
}

function requestId(state: StudioState): number {
  if (state.flow.kind !== "recognizing") {
    throw new Error(`expected recognizing, got ${state.flow.kind}`);
  }
  return state.flow.requestId;
}

const drawn = run(INITIAL_STUDIO, ...LINE);
const sent = run(drawn, { type: "recognize", canvas: CANVAS });

describe("recognize", () => {
  it("needs strokes and a finished gesture", () => {
    expect(canRecognize(INITIAL_STUDIO)).toBe(false);
    expect(run(INITIAL_STUDIO, { type: "recognize", canvas: CANVAS })).toBe(INITIAL_STUDIO);
    const midStroke = run(drawn, ...sketch({ type: "begin", point: [5, 5], width: 8 }));
    expect(canRecognize(midStroke)).toBe(false);
    expect(canRecognize(drawn)).toBe(true);
  });

  it("sends the strokes as they were when the button was pressed", () => {
    expect(sent.flow).toEqual({ kind: "recognizing", requestId: 1, request: toRequest(drawn.sketch.strokes, CANVAS) });
  });

  it("locks the canvas while waiting", () => {
    expect(run(sent, ...sketch({ type: "undo" }), ...sketch({ type: "clear" }))).toBe(sent);
  });

  it("ignores an answer to an older request", () => {
    const stale = run(sent, { type: "resolved", requestId: requestId(sent) + 5, prediction: prediction(false) });
    expect(stale).toBe(sent);
  });
});

describe("confirm and pick", () => {
  it("a confident answer is confirmed with one tap and the sketch is cleared", () => {
    const suggested = run(sent, { type: "resolved", requestId: requestId(sent), prediction: prediction(false) });
    expect(suggested.flow.kind).toBe("suggested");
    const placed = run(suggested, { type: "confirm" });
    expect(placed.placed).toEqual([
      expect.objectContaining({ label: "sun", picked: false, bounds: { minX: 20, minY: 30, maxX: 220, maxY: 90 } }),
    ]);
    expect(placed.sketch.strokes).toEqual([]);
    expect(placed.flow.kind).toBe("drawing");
  });

  it("an uncertain answer is never placed without a pick", () => {
    const choosing = run(sent, { type: "resolved", requestId: requestId(sent), prediction: prediction(true) });
    expect(choosing.flow.kind).toBe("choosing");
    expect(run(choosing, { type: "confirm" })).toBe(choosing);
    const picked = run(choosing, { type: "pick", label: "flower" });
    expect(picked.placed.map((item) => [item.label, item.picked])).toEqual([["flower", true]]);
  });

  it("hands placements to the world once and never reuses an id", () => {
    const suggested = run(sent, { type: "resolved", requestId: requestId(sent), prediction: prediction(false) });
    const first = run(suggested, { type: "confirm" });
    const handed = run(first, { type: "spawned", id: first.placed[0].id });
    expect(handed.placed).toEqual([]);
    expect(run(handed, { type: "spawned", id: 1 })).toBe(handed);

    const again = run(handed, ...LINE, { type: "recognize", canvas: CANVAS });
    const second = run(again, { type: "resolved", requestId: requestId(again), prediction: prediction(false) }, { type: "confirm" });
    expect(second.placed.map((item) => item.id)).toEqual([2]);
  });

  it("any of the six can be picked, including ones outside the top three", () => {
    const suggested = run(sent, { type: "resolved", requestId: requestId(sent), prediction: prediction(false) });
    for (const label of LABELS) {
      const placed = run(suggested, { type: "pick", label });
      expect(placed.placed[0].label).toBe(label);
      expect(placed.placed[0].picked).toBe(label !== "sun");
    }
  });
});

describe("retry keeps the sketch", () => {
  it("drawing more after an answer drops the answer and keeps the strokes", () => {
    const suggested = run(sent, { type: "resolved", requestId: requestId(sent), prediction: prediction(false) });
    const revised = run(suggested, { type: "revise" });
    expect(revised.flow.kind).toBe("drawing");
    expect(revised.sketch.strokes).toBe(suggested.sketch.strokes);

    const edited = run(suggested, ...sketch({ type: "begin", point: [300, 200], width: 8 }, { type: "end" }));
    expect(edited.flow.kind).toBe("drawing");
    expect(edited.sketch.strokes).toHaveLength(2);
  });

  it("a failure can be retried with the same sketch", () => {
    const failed = run(sent, {
      type: "rejected",
      requestId: requestId(sent),
      error: { code: "unreachable", message: "Could not reach the recognizer." },
    });
    expect(failed.flow).toMatchObject({ kind: "failed", error: { code: "unreachable" } });
    const again = run(failed, { type: "retry" });
    expect(again.flow).toMatchObject({ kind: "recognizing", requestId: requestId(sent) + 1 });
    expect(again.flow.kind === "recognizing" && again.flow.request).toEqual(toRequest(drawn.sketch.strokes, CANVAS));
    expect(again.sketch).toBe(failed.sketch);
    expect(run(failed, { type: "revise" }).sketch).toBe(failed.sketch);
  });
});
