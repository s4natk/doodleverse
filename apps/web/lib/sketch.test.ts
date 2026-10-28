import { describe, expect, it } from "vitest";

import { MAX_POINTS, MAX_STROKES } from "./contract";
import { boundsOf, distanceToPolyline, type Point } from "./geometry";
import { EMPTY_SKETCH, pointCount, sketchReducer, type SketchAction, type SketchState } from "./sketch";

function run(state: SketchState, ...actions: SketchAction[]): SketchState {
  return actions.reduce(sketchReducer, state);
}

function draw(state: SketchState, points: Point[], width = 6): SketchState {
  return run(state, { type: "begin", point: points[0], width }, { type: "extend", points: points.slice(1) }, { type: "end" });
}

const LINE: Point[] = [[10, 10], [40, 10], [70, 10]];
const POST: Point[] = [[200, 20], [200, 90]];

describe("drawing", () => {
  it("keeps a finished stroke and drops points that barely move", () => {
    const state = draw(EMPTY_SKETCH, [[0, 0], [0.5, 0.5], [5, 0], [5.4, 0.2], [12, 0]]);
    expect(state.strokes).toHaveLength(1);
    expect(state.strokes[0].points).toEqual([[0, 0], [5, 0], [12, 0]]);
    expect(state.active).toBeNull();
  });

  it("keeps a tap as a one-point stroke", () => {
    const state = draw(EMPTY_SKETCH, [[30, 30]]);
    expect(state.strokes[0].points).toEqual([[30, 30]]);
  });

  it("drops a cancelled stroke", () => {
    const state = run(EMPTY_SKETCH, { type: "begin", point: [1, 1], width: 6 }, { type: "cancel" });
    expect(state.strokes).toEqual([]);
    expect(state.history).toEqual([]);
  });

  it("stops at the stroke and point limits the service enforces", () => {
    let state = EMPTY_SKETCH;
    for (let index = 0; index < MAX_STROKES + 5; index += 1) {
      state = draw(state, [[index, index]]);
    }
    expect(state.strokes).toHaveLength(MAX_STROKES);

    const long: Point[] = Array.from({ length: MAX_POINTS + 500 }, (_, index) => [index * 2, 0] as Point);
    const full = draw(EMPTY_SKETCH, long);
    expect(pointCount(full.strokes)).toBe(MAX_POINTS);
    expect(draw(full, [[1, 1]]).strokes).toHaveLength(1);
  });
});

describe("undo and clear", () => {
  it("undo removes strokes newest first, then does nothing", () => {
    const two = draw(draw(EMPTY_SKETCH, LINE), POST);
    const one = run(two, { type: "undo" });
    expect(one.strokes.map((stroke) => stroke.points)).toEqual([LINE]);
    const none = run(one, { type: "undo" });
    expect(none.strokes).toEqual([]);
    expect(run(none, { type: "undo" })).toBe(none);
  });

  it("clear empties the sketch and can be undone", () => {
    const two = draw(draw(EMPTY_SKETCH, LINE), POST);
    const cleared = run(two, { type: "clear" });
    expect(cleared.strokes).toEqual([]);
    expect(run(cleared, { type: "clear" })).toBe(cleared);
    expect(run(cleared, { type: "undo" }).strokes).toEqual(two.strokes);
  });

  it("ignores undo and clear in the middle of a stroke", () => {
    const drawing = run(draw(EMPTY_SKETCH, LINE), { type: "begin", point: [5, 5], width: 6 });
    expect(run(drawing, { type: "undo" })).toBe(drawing);
    expect(run(drawing, { type: "clear" })).toBe(drawing);
  });
});

describe("eraser", () => {
  const sketch = draw(draw(EMPTY_SKETCH, LINE), POST);

  it("removes the whole stroke it touches and leaves the rest", () => {
    const erased = run(sketch, { type: "eraseBegin" }, { type: "erase", point: [40, 14], radius: 4 }, { type: "eraseEnd" });
    expect(erased.strokes.map((stroke) => stroke.points)).toEqual([POST]);
  });

  it("counts the stroke width when deciding what it touches", () => {
    const wide = draw(EMPTY_SKETCH, LINE, 20);
    const hit = run(wide, { type: "eraseBegin" }, { type: "erase", point: [40, 22], radius: 3 }, { type: "eraseEnd" });
    expect(hit.strokes).toEqual([]);
  });

  it("makes one swipe across several strokes a single undo step", () => {
    const swiped = run(
      sketch,
      { type: "eraseBegin" },
      { type: "erase", point: [40, 10], radius: 4 },
      { type: "erase", point: [200, 50], radius: 4 },
      { type: "eraseEnd" },
    );
    expect(swiped.strokes).toEqual([]);
    expect(run(swiped, { type: "undo" }).strokes).toEqual(sketch.strokes);
  });

  it("adds no undo step when it misses", () => {
    const missed = run(sketch, { type: "eraseBegin" }, { type: "erase", point: [400, 400], radius: 4 }, { type: "eraseEnd" });
    expect(missed.strokes).toBe(sketch.strokes);
    expect(missed.history).toBe(sketch.history);
  });

  it("does nothing outside an eraser gesture", () => {
    expect(run(sketch, { type: "erase", point: [40, 10], radius: 4 })).toBe(sketch);
  });
});

describe("geometry", () => {
  it("measures to the nearest segment, or to a dot", () => {
    expect(distanceToPolyline([5, 3], [[0, 0], [10, 0]])).toBe(3);
    expect(distanceToPolyline([13, 4], [[0, 0], [10, 0]])).toBe(5);
    expect(distanceToPolyline([3, 4], [[0, 0]])).toBe(5);
  });

  it("bounds every point of every stroke", () => {
    expect(boundsOf([LINE, POST])).toEqual({ minX: 10, minY: 10, maxX: 200, maxY: 90 });
    expect(boundsOf([])).toBeNull();
  });
});
