import { describe, expect, it } from "vitest";

import type { Label } from "../contract";
import { STEP } from "./clock";
import { WORLD_WIDTH, type Sketch } from "./layout";
import { mixColor } from "./palette";
import {
  clearWorld,
  createWorld,
  pose,
  resetWorld,
  SAPLING,
  spawn,
  SPAWN_SECONDS,
  step,
  SUN_LIGHT,
  SUN_PULSE,
  TREE_GROW_SECONDS,
  type World,
} from "./sim";

function sketch(label: Label, minX = 100, minY = 100, size = 60): Sketch {
  return {
    label,
    strokes: [{ points: [[minX, minY], [minX + size, minY + size]], width: 8 }],
    bounds: { minX, minY, maxX: minX + size, maxY: minY + size },
    canvas: { width: 960, height: 720 },
  };
}

function run(world: World, seconds: number): void {
  for (let index = 0; index < Math.round(seconds / STEP); index += 1) {
    step(world);
  }
}

describe("spawning", () => {
  it("starts where it was drawn and settles where its class lives", () => {
    const world = createWorld();
    const tree = spawn(world, sketch("tree", 300, 100, 200));
    const start = pose(tree);
    expect([start.x, start.y, start.scale]).toEqual([400, 300, 1]);
    run(world, SPAWN_SECONDS + STEP);
    const end = pose(tree);
    expect(end.settled).toBe(1);
    expect([end.x, end.y]).toEqual([tree.rest.x, tree.rest.y]);
    expect(end.scale).toBeCloseTo(tree.rest.scale * SAPLING, 1);
  });

  it("closes in on the resting spot every step of the move", () => {
    const world = createWorld();
    const sun = spawn(world, sketch("sun", 400, 500, 80));
    let distance = Infinity;
    for (let index = 0; index < SPAWN_SECONDS / STEP; index += 1) {
      const now = pose(sun);
      const next = Math.hypot(now.x - sun.rest.x, now.y - sun.rest.y);
      expect(next).toBeLessThanOrEqual(distance + 1e-9);
      distance = next;
      step(world);
    }
  });

  it("places and phases the same sketch the same way every time", () => {
    const first = spawn(createWorld(), sketch("cloud"));
    const again = spawn(createWorld(), sketch("cloud"));
    expect([again.rest, again.phase, again.drift]).toEqual([first.rest, first.phase, first.drift]);
  });
});

describe("sun", () => {
  it("pulses a few percent, glows, and brings daylight", () => {
    const world = createWorld();
    const sun = spawn(world, sketch("sun"));
    let low = Infinity;
    let high = 0;
    for (let index = 0; index < 8 / STEP; index += 1) {
      step(world);
      const now = pose(sun);
      if (now.settled === 1) {
        low = Math.min(low, now.scale / sun.rest.scale);
        high = Math.max(high, now.scale / sun.rest.scale);
        expect(now.glow).toBeGreaterThan(0.3);
      }
    }
    expect(low).toBeCloseTo(1 - SUN_PULSE, 2);
    expect(high).toBeCloseTo(1 + SUN_PULSE, 2);
    expect(world.sunlight).toBeCloseTo(SUN_LIGHT, 2);
  });

  it("fades the daylight once the sun is gone", () => {
    const world = createWorld();
    spawn(world, sketch("sun"));
    run(world, 8);
    world.entities.length = 0;
    run(world, 8);
    expect(world.sunlight).toBeLessThan(0.01);
  });

  it("does not pulse in step with a second sun", () => {
    const world = createWorld();
    const [one, two] = [spawn(world, sketch("sun")), spawn(world, sketch("sun", 600))];
    run(world, 2);
    expect(pose(one).scale / one.rest.scale).not.toBeCloseTo(pose(two).scale / two.rest.scale, 3);
    expect(world.sunlight).toBeGreaterThan(SUN_LIGHT - 0.2);
  });
});

describe("cloud", () => {
  it("drifts only after it settles, and wraps around the edges", () => {
    const world = createWorld();
    const cloud = spawn(world, sketch("cloud", 400, 80, 120));
    run(world, SPAWN_SECONDS - STEP);
    expect(cloud.x).toBe(cloud.rest.x);
    run(world, 1);
    expect(Math.sign(cloud.x - cloud.rest.x)).toBe(Math.sign(cloud.drift));
    const half = (cloud.drawing.width * cloud.rest.scale) / 2;
    run(world, (WORLD_WIDTH + 2 * half) / Math.abs(cloud.drift) + 1);
    expect(cloud.x).toBeGreaterThan(-half - 1);
    expect(cloud.x).toBeLessThan(WORLD_WIDTH + half + 1);
  });
});

describe("tree", () => {
  it("grows from a sapling to full size and stops", () => {
    const world = createWorld();
    const tree = spawn(world, sketch("tree", 300, 300, 200));
    run(world, SPAWN_SECONDS + STEP);
    let previous = pose(tree).scale;
    for (let second = 0; second < TREE_GROW_SECONDS; second += 1) {
      run(world, 1);
      const now = pose(tree).scale;
      expect(now).toBeGreaterThan(previous);
      previous = now;
    }
    run(world, 5);
    expect(pose(tree).scale).toBeCloseTo(tree.rest.scale, 6);
  });
});

describe("clear and reset", () => {
  it("clear empties the world and lets the daylight fade", () => {
    const world = createWorld();
    spawn(world, sketch("sun"));
    spawn(world, sketch("tree"));
    run(world, 6);
    clearWorld(world);
    expect(world.entities).toEqual([]);
    expect(world.sunlight).toBeGreaterThan(0.5);
    run(world, 8);
    expect(world.sunlight).toBeLessThan(0.01);
  });

  it("reset is dark at once, and new entities never reuse an id", () => {
    const world = createWorld();
    const before = spawn(world, sketch("sun"));
    run(world, 6);
    resetWorld(world);
    expect([world.entities.length, world.sunlight]).toEqual([0, 0]);
    expect(spawn(world, sketch("cloud")).id).toBeGreaterThan(before.id);
  });
});

describe("palette", () => {
  it("mixes colors channel by channel", () => {
    expect(mixColor(0x000000, 0xffffff, 0.5)).toBe(0x808080);
    expect(mixColor(0x102030, 0x102030, 0.7)).toBe(0x102030);
    expect(mixColor(0xff0000, 0x0000ff, 2)).toBe(0x0000ff);
  });
});
