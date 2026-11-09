import { describe, expect, it } from "vitest";

import type { Label } from "../contract";
import { PATH_BOTTOM, PATH_TOP, steer, type CatState } from "./cats";
import { STEP } from "./clock";
import type { Sketch } from "./layout";
import { CAT_RADIUS, CAT_REACT_DISTANCE, SPAWN_SECONDS, TRUNK_FRACTION, TRUNK_MIN } from "./rules";
import { createWorld, pose, spawn, step, type Entity, type World } from "./sim";

function sketch(label: Label, minX: number, baseY: number, size: number): Sketch {
  return {
    label,
    strokes: [{ points: [[minX, baseY - size], [minX + size, baseY]], width: 8 }],
    bounds: { minX, minY: baseY - size, maxX: minX + size, maxY: baseY },
    canvas: { width: 960, height: 720 },
  };
}

function run(world: World, seconds: number, each?: () => void): void {
  for (let index = 0; index < Math.round(seconds / STEP); index += 1) {
    step(world);
    each?.();
  }
}

function settledCat(world: World, x: number, y = 640): Entity & { cat: CatState } {
  const cat = spawn(world, sketch("cat", x - 40, y, 80)) as Entity & { cat: CatState };
  run(world, SPAWN_SECONDS + STEP);
  return cat;
}

describe("cat", () => {
  it("sits, walks to a spot on the ground, and sits again", () => {
    const world = createWorld();
    const cat = settledCat(world, 300);
    const moods = new Set<string>();
    let lowest = Infinity;
    let highest = -Infinity;
    run(world, 30, () => {
      moods.add(cat.cat.mood);
      lowest = Math.min(lowest, cat.y);
      highest = Math.max(highest, cat.y);
    });
    expect(moods).toEqual(new Set(["idle", "walk"]));
    expect(cat.cat.walks).toBeGreaterThanOrEqual(2);
    expect(lowest).toBeGreaterThanOrEqual(PATH_TOP);
    expect(highest).toBeLessThanOrEqual(PATH_BOTTOM);
  });

  it("goes round a tree in its way and still gets where it was going", () => {
    const world = createWorld();
    spawn(world, sketch("tree", 400, 640, 200));
    const cat = settledCat(world, 100);
    Object.assign(cat.cat, { mood: "walk", timer: 60, target: { x: 800, y: 640 } });
    let closest = Infinity;
    let reached = false;
    run(world, 20, () => {
      if (cat.cat.walks === 0) {
        closest = Math.min(closest, Math.hypot(cat.x - 500, cat.y - 640));
        reached ||= Math.hypot(cat.x - 800, cat.y - 640) < 10;
      }
    });
    const trunk = Math.max(TRUNK_MIN, 200 * TRUNK_FRACTION);
    expect(closest).toBeGreaterThan(trunk + CAT_RADIUS - 2);
    expect(reached).toBe(true);
  });

  it("hops and runs the other way when a car comes close, then calms down", () => {
    const world = createWorld();
    const cat = settledCat(world, 500);
    const car = spawn(world, sketch("car", 330, 650, 120));
    car.facing = 1;
    car.startFacing = 1;
    let hopped = 0;
    let fled = false;
    run(world, 3, () => {
      hopped = Math.max(hopped, cat.y - pose(cat).y);
      fled ||= cat.cat.mood === "flee";
    });
    expect(fled).toBe(true);
    expect(hopped).toBeGreaterThan(10);
    expect(cat.x).toBeGreaterThan(500 + 100);
    expect(cat.facing).toBe(1);
  });

  it("ignores a car that is far away", () => {
    const world = createWorld();
    const cat = settledCat(world, 800);
    const car = spawn(world, sketch("car", 60, 650, 120));
    let startled = false;
    run(world, 1.5, () => {
      startled ||= cat.cat.mood === "flee" || cat.cat.hop >= 0;
    });
    expect(Math.abs(cat.x - car.x)).toBeGreaterThan(CAT_REACT_DISTANCE);
    expect(startled).toBe(false);
  });

  it("steers straight when nothing is in the way", () => {
    const { vx, vy } = steer({ x: 0, y: 640 }, { x: 100, y: 640 }, 50, []);
    expect([vx, vy]).toEqual([50, 0]);
    expect(steer({ x: 5, y: 5 }, { x: 5, y: 5 }, 50, [])).toEqual({ vx: 0, vy: 0 });
  });
});
