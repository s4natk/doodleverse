import { describe, expect, it } from "vitest";

import { advance, createClock, MAX_STEPS, STEP } from "./clock";
import { GROUND_Y, restPosition, restScale, SIZE, toWorld, WORLD_WIDTH, type Sketch } from "./layout";

function frames(clock: ReturnType<typeof createClock>, count: number, ms: number): number {
  let steps = 0;
  for (let index = 0; index < count; index += 1) {
    steps += advance(clock, ms);
  }
  return steps;
}

// Float rounding can leave the last step owed until the next frame.
function expectWithinOneStep(steps: number, expected: number): void {
  expect(Math.abs(steps - expected)).toBeLessThanOrEqual(1);
}

describe("fixed-timestep clock", () => {
  it("runs sixty steps for a second of frames, at any frame rate", () => {
    expectWithinOneStep(frames(createClock(), 60, 1000 / 60), 60);
    expectWithinOneStep(frames(createClock(), 144, 1000 / 144), 60);
    expectWithinOneStep(frames(createClock(), 30, 1000 / 30), 60);
  });

  it("scales world time by the speed", () => {
    const fast = createClock();
    fast.speed = 2;
    expectWithinOneStep(frames(fast, 60, 1000 / 60), 120);
    const slow = createClock();
    slow.speed = 0.5;
    expectWithinOneStep(frames(slow, 60, 1000 / 60), 30);
    expect(Math.abs(slow.time - 0.5)).toBeLessThanOrEqual(STEP);
  });

  it("stops while paused and keeps the time it owed", () => {
    const clock = createClock();
    advance(clock, 10);
    const owed = clock.owed;
    clock.paused = true;
    expect(frames(clock, 30, 16)).toBe(0);
    expect(clock.owed).toBe(owed);
  });

  it("does not replay a long gap", () => {
    const clock = createClock();
    expect(advance(clock, 5000)).toBe(MAX_STEPS);
    expect(clock.owed).toBe(0);
    expect(clock.time).toBeCloseTo(MAX_STEPS * STEP, 9);
  });
});

const SUN: Sketch = {
  label: "sun",
  strokes: [{ points: [[100, 50], [140, 90]], width: 8 }],
  bounds: { minX: 100, minY: 50, maxX: 140, maxY: 90 },
  canvas: { width: 480, height: 360 },
};

describe("placing a drawing in the world", () => {
  it("scales canvas pixels to world units around the anchor", () => {
    const { drawing, at } = toWorld(SUN);
    expect(at).toEqual([240, 140]);
    expect(drawing.strokes[0]).toEqual({ points: [[-40, -40], [40, 40]], width: 16 });
    expect([drawing.width, drawing.height]).toEqual([80, 80]);
  });

  it("hangs ground things from the bottom of the drawing", () => {
    const { at } = toWorld({ ...SUN, label: "tree" });
    expect(at).toEqual([240, 180]);
  });

  it("brings the longest side into the class's size range", () => {
    const { drawing } = toWorld(SUN);
    expect(drawing.width * restScale("sun", drawing)).toBe(SIZE.sun[0]);
    const huge = { ...drawing, width: 900, height: 300 };
    expect(huge.width * restScale("cloud", huge)).toBe(SIZE.cloud[1]);
    const fits = { ...drawing, width: 200, height: 120 };
    expect(restScale("tree", fits)).toBe(1);
  });

  it("keeps suns in the sky, puts trees on the ground, and keeps both on screen", () => {
    const drawing = { strokes: [], width: 100, height: 100 };
    expect(restPosition("sun", [480, 650], drawing, 1)).toEqual([480, 240]);
    expect(restPosition("tree", [480, 200], drawing, 1)).toEqual([480, GROUND_Y]);
    expect(restPosition("tree", [480, 640], drawing, 1)).toEqual([480, 640]);
    const [x] = restPosition("cloud", [WORLD_WIDTH + 50, 100], drawing, 1);
    expect(x).toBe(WORLD_WIDTH - 50 - 12);
  });
});
