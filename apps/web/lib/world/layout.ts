import type { Label } from "../contract";
import type { Bounds, Point } from "../geometry";

/** World units. The scene scales this box to fit its 4:3 frame. */
export const WORLD_WIDTH = 960;
export const WORLD_HEIGHT = 720;
export const GROUND_Y = 600;
const EDGE = 12;

/** Where an entity hangs from: its middle in the sky, the bottom of its drawing on the ground. */
export type Anchor = "center" | "base";

export const ANCHOR: Record<Label, Anchor> = {
  sun: "center",
  cloud: "center",
  tree: "base",
  flower: "base",
  car: "base",
  cat: "base",
};

/** Longest side an entity settles at, in world units. Drawings outside the range are scaled into it. */
export const SIZE: Record<Label, readonly [number, number]> = {
  sun: [110, 170],
  cloud: [150, 250],
  tree: [150, 260],
  flower: [70, 130],
  car: [120, 200],
  cat: [80, 150],
};

export type DrawingStroke = { points: Point[]; width: number };

/** Strokes in world units, relative to the anchor. */
export type Drawing = { strokes: DrawingStroke[]; width: number; height: number };

export type Sketch = {
  label: Label;
  strokes: { points: readonly Point[]; width: number }[];
  bounds: Bounds;
  canvas: { width: number; height: number };
};

export function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

/** The drawing in world units and the world point it hangs from, where it was drawn. */
export function toWorld(sketch: Sketch): { drawing: Drawing; at: Point } {
  const k = Math.min(WORLD_WIDTH / sketch.canvas.width, WORLD_HEIGHT / sketch.canvas.height);
  const { minX, minY, maxX, maxY } = sketch.bounds;
  const at: Point = [((minX + maxX) / 2) * k, (ANCHOR[sketch.label] === "base" ? maxY : (minY + maxY) / 2) * k];
  const strokes = sketch.strokes.map((stroke) => ({
    points: stroke.points.map(([x, y]): Point => [x * k - at[0], y * k - at[1]]),
    width: stroke.width * k,
  }));
  return { drawing: { strokes, width: (maxX - minX) * k, height: (maxY - minY) * k }, at };
}

export function restScale(label: Label, drawing: Drawing): number {
  const longest = Math.max(drawing.width, drawing.height, 1);
  const [low, high] = SIZE[label];
  return clamp(longest, low, high) / longest;
}

/** Near where it was drawn, but on screen: suns and clouds stay in the sky, the rest stand on the ground. */
export function restPosition(label: Label, at: Point, drawing: Drawing, scale: number): Point {
  const halfWidth = (drawing.width * scale) / 2;
  const height = drawing.height * scale;
  const x = clamp(at[0], halfWidth + EDGE, WORLD_WIDTH - halfWidth - EDGE);
  if (label === "sun") {
    return [x, clamp(at[1], height / 2 + EDGE, 240)];
  }
  if (label === "cloud") {
    return [x, clamp(at[1], height / 2 + EDGE, 320)];
  }
  return [x, clamp(at[1], GROUND_Y, GROUND_Y + 80)];
}
