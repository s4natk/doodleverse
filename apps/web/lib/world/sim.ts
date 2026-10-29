import type { Label } from "../contract";
import { STEP } from "./clock";
import { restPosition, restScale, toWorld, WORLD_WIDTH, type Drawing, type Sketch } from "./layout";

/** Seconds a confirmed drawing takes to move from where it was drawn to where it settles. */
export const SPAWN_SECONDS = 0.6;
export const TREE_GROW_SECONDS = 12;
/** A new tree starts at this fraction of its grown size. */
export const SAPLING = 0.35;
export const SUN_PULSE = 0.05;
/** Daylight one sun brings, out of 1. Two or more bring full day. */
export const SUN_LIGHT = 0.85;
const LIGHT_EASE_SECONDS = 1.2;

type Placement = { x: number; y: number; scale: number };

export type Entity = {
  id: number;
  label: Label;
  drawing: Drawing;
  /** Where and how big it was drawn, in world units. */
  from: Placement;
  /** Where it settles, at the scale of its grown self. */
  rest: Placement;
  /** World seconds since it was confirmed. */
  age: number;
  /** Offset into its cycles, so two suns do not pulse in step. */
  phase: number;
  /** World units per second. Only clouds drift. */
  drift: number;
  x: number;
};

export type Pose = {
  x: number;
  y: number;
  scale: number;
  rotation: number;
  /** Sun glow strength, 0 to 1. */
  glow: number;
  /** How far the spawn move has come, 0 to 1. */
  settled: number;
};

export type World = { entities: Entity[]; sunlight: number; nextId: number };

export function createWorld(): World {
  return { entities: [], sunlight: 0, nextId: 1 };
}

// Same id, same number: placement and cycles do not change between runs.
function unit(id: number, salt: number): number {
  const value = Math.sin(id * 12.9898 + salt * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

export function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3;
}

function lerp(from: number, to: number, t: number): number {
  return from + (to - from) * t;
}

export function spawn(world: World, sketch: Sketch): Entity {
  const { drawing, at } = toWorld(sketch);
  const scale = restScale(sketch.label, drawing);
  const [x, y] = restPosition(sketch.label, at, drawing, scale);
  const id = world.nextId;
  const direction = unit(id, 1) < 0.5 ? -1 : 1;
  const entity: Entity = {
    id,
    label: sketch.label,
    drawing,
    from: { x: at[0], y: at[1], scale: 1 },
    rest: { x, y, scale },
    age: 0,
    phase: unit(id, 2) * Math.PI * 2,
    drift: sketch.label === "cloud" ? direction * (12 + 14 * unit(id, 3)) : 0,
    x,
  };
  world.nextId += 1;
  world.entities.push(entity);
  return entity;
}

/** Removes every entity. Daylight fades on its own. */
export function clearWorld(world: World): void {
  world.entities.length = 0;
}

/** Back to the empty, unlit world it started as. Ids keep counting up. */
export function resetWorld(world: World): void {
  clearWorld(world);
  world.sunlight = 0;
}

function wrap(entity: Entity, x: number): number {
  const half = (entity.drawing.width * entity.rest.scale) / 2;
  if (x - half > WORLD_WIDTH) {
    return -half;
  }
  if (x + half < 0) {
    return WORLD_WIDTH + half;
  }
  return x;
}

export function step(world: World, dt = STEP): void {
  let suns = 0;
  for (const entity of world.entities) {
    entity.age += dt;
    if (entity.label === "sun") {
      suns += 1;
    }
    if (entity.drift !== 0 && entity.age > SPAWN_SECONDS) {
      entity.x = wrap(entity, entity.x + entity.drift * dt);
    }
  }
  const daylight = Math.min(1, suns * SUN_LIGHT);
  world.sunlight += (daylight - world.sunlight) * (1 - Math.exp(-dt / LIGHT_EASE_SECONDS));
}

/** The pose after settling, `t` world seconds in. */
function settledPose(entity: Entity, t: number): Pose {
  const { rest, phase } = entity;
  const base: Pose = { x: rest.x, y: rest.y, scale: rest.scale, rotation: 0, glow: 0, settled: 1 };
  switch (entity.label) {
    case "sun": {
      const wave = Math.sin((2 * Math.PI * t) / 4 + phase);
      return { ...base, scale: rest.scale * (1 + SUN_PULSE * wave), glow: 0.6 + 0.2 * wave };
    }
    case "cloud":
      return { ...base, x: entity.x, y: rest.y + 4 * Math.sin((2 * Math.PI * t) / 6 + phase) };
    case "tree": {
      const grown = easeOutCubic(Math.min(1, t / TREE_GROW_SECONDS));
      return { ...base, scale: rest.scale * (SAPLING + (1 - SAPLING) * grown) };
    }
    default:
      return { ...base, rotation: 0.03 * Math.sin((2 * Math.PI * t) / 3 + phase) };
  }
}

export function pose(entity: Entity): Pose {
  const settled = Math.min(1, entity.age / SPAWN_SECONDS);
  const resting = settledPose(entity, Math.max(0, entity.age - SPAWN_SECONDS));
  if (settled >= 1) {
    return resting;
  }
  const t = easeOutCubic(settled);
  return {
    x: lerp(entity.from.x, resting.x, t),
    y: lerp(entity.from.y, resting.y, t),
    scale: lerp(entity.from.scale, resting.scale, t),
    rotation: lerp(0, resting.rotation, t),
    glow: resting.glow * t,
    settled,
  };
}
