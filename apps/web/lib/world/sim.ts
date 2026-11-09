import type { Label } from "../contract";
import { addCar, carPose, createTraffic, removeCars, stepTraffic, type Traffic } from "./cars";
import { createCat, hopHeight, stepCat, type CatState, type Surroundings } from "./cats";
import { STEP } from "./clock";
import { restPosition, restScale, toWorld, WORLD_WIDTH, type Drawing, type Sketch } from "./layout";
import { unit } from "./random";
import {
  BLOOM_LIGHT,
  BLOOM_SECONDS,
  BLOOM_SWELL,
  BLOOM_WATER,
  BUD,
  CAR_SPEED_MIN,
  CAR_SPEED_RANGE,
  CLOUD_BOB,
  CLOUD_BOB_SECONDS,
  CLOUD_DRIFT_MIN,
  CLOUD_DRIFT_RANGE,
  DRY_SECONDS,
  FLOWER_GROW_SECONDS,
  FLOWER_SWAY,
  FLOWER_SWAY_SECONDS,
  LIGHT_EASE_SECONDS,
  RAIN_GROWTH,
  RAIN_MAX_GROWTH,
  RAIN_WATER,
  RAIN_WIDTH,
  SAPLING,
  SPAWN_SECONDS,
  SUN_GLOW,
  SUN_GLOW_PULSE,
  SUN_LIGHT,
  SUN_PERIOD_SECONDS,
  SUN_PULSE,
  SWAY,
  SWAY_SECONDS,
  TAP_SLOP,
  TREE_GROW_SECONDS,
  TRUNK_FRACTION,
  TRUNK_MIN,
  WILT_SECONDS,
} from "./rules";

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
  /** Where things that move are now: clouds across the sky, cars and cats along the ground. */
  x: number;
  y: number;
  /** 1 heading right, -1 heading left. The drawing is mirrored once this differs from `startFacing`. */
  facing: number;
  startFacing: number;
  /** Cars: cruising speed in world units per second. */
  speed: number;
  rotation: number;
  /** Trees and flowers: 0 as a sapling or bud, 1 fully grown. Rain can take a tree past 1. */
  growth: number;
  /** Flowers: rain soaked in, 0 to 1. */
  water: number;
  /** Flowers: 0 closed, 1 fully open. */
  bloom: number;
  /** Clouds: whether it is raining. */
  raining: boolean;
  /** Cats: what it is up to. */
  cat: CatState | null;
};

export type Pose = {
  x: number;
  y: number;
  scale: number;
  rotation: number;
  /** -1 when the drawing is shown mirrored. */
  mirror: number;
  /** Sun glow strength, 0 to 1. */
  glow: number;
  /** Flowers: how open, 0 to 1. */
  bloom: number;
  /** How far the spawn move has come, 0 to 1. */
  settled: number;
};

export type World = {
  entities: Entity[];
  sunlight: number;
  nextId: number;
  traffic: Traffic;
};

export function createWorld(): World {
  return { entities: [], sunlight: 0, nextId: 1, traffic: createTraffic(STEP) };
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
    drift: sketch.label === "cloud" ? direction * (CLOUD_DRIFT_MIN + CLOUD_DRIFT_RANGE * unit(id, 3)) : 0,
    x,
    y,
    facing: direction,
    startFacing: direction,
    speed: sketch.label === "car" ? CAR_SPEED_MIN + CAR_SPEED_RANGE * unit(id, 5) : 0,
    rotation: 0,
    growth: 0,
    water: 0,
    bloom: 0,
    raining: false,
    cat: sketch.label === "cat" ? createCat(id) : null,
  };
  world.nextId += 1;
  world.entities.push(entity);
  return entity;
}

/** Turns rain on or off for the settled cloud at (x, y), the newest one if they overlap. */
export function tapCloud(world: World, x: number, y: number): Entity | null {
  for (let index = world.entities.length - 1; index >= 0; index -= 1) {
    const cloud = world.entities[index];
    if (cloud.label !== "cloud" || cloud.age <= SPAWN_SECONDS) {
      continue;
    }
    const now = pose(cloud);
    const halfWidth = (cloud.drawing.width * now.scale) / 2 + TAP_SLOP;
    const halfHeight = (cloud.drawing.height * now.scale) / 2 + TAP_SLOP;
    if (Math.abs(x - now.x) <= halfWidth && Math.abs(y - now.y) <= halfHeight) {
      cloud.raining = !cloud.raining;
      return cloud;
    }
  }
  return null;
}

/** Removes every entity and its physics body. Daylight fades on its own. */
export function clearWorld(world: World): void {
  world.entities.length = 0;
  removeCars(world.traffic);
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

function approach(value: number, target: number, amount: number): number {
  return value < target ? Math.min(target, value + amount) : Math.max(target, value - amount);
}

/** The stretch of ground a raining cloud waters, or null when it is dry or still settling. */
export function rainSpan(entity: Entity): [number, number] | null {
  if (!entity.raining || entity.age <= SPAWN_SECONDS) {
    return null;
  }
  const half = (entity.drawing.width * entity.rest.scale * RAIN_WIDTH) / 2;
  return [entity.x - half, entity.x + half];
}

function rainedOn(world: World, x: number): boolean {
  return world.entities.some((cloud) => {
    const span = rainSpan(cloud);
    return span !== null && x >= span[0] && x <= span[1];
  });
}

function grow(world: World, entity: Entity, dt: number): void {
  const wet = rainedOn(world, entity.rest.x);
  if (entity.label === "tree") {
    if (wet) {
      entity.growth = Math.min(RAIN_MAX_GROWTH, entity.growth + (RAIN_GROWTH * dt) / TREE_GROW_SECONDS);
    } else if (entity.growth < 1) {
      entity.growth = Math.min(1, entity.growth + dt / TREE_GROW_SECONDS);
    }
    return;
  }
  entity.growth = Math.min(1, entity.growth + dt / FLOWER_GROW_SECONDS);
  entity.water = wet ? Math.min(1, entity.water + RAIN_WATER * dt) : Math.max(0, entity.water - dt / DRY_SECONDS);
  if (world.sunlight >= BLOOM_LIGHT && entity.water >= BLOOM_WATER) {
    entity.bloom = approach(entity.bloom, 1, dt / BLOOM_SECONDS);
  } else if (world.sunlight < BLOOM_LIGHT) {
    entity.bloom = approach(entity.bloom, 0, dt / WILT_SECONDS);
  }
}

/** What a cat steers around and shies away from: tree trunks and settled cars. */
function surroundings(world: World): Surroundings {
  const trees = world.entities
    .filter((entity) => entity.label === "tree")
    .map((tree) => ({
      x: tree.rest.x,
      y: tree.rest.y,
      r: Math.max(TRUNK_MIN, tree.drawing.width * tree.rest.scale * TRUNK_FRACTION),
    }));
  const cars = world.entities
    .filter((entity) => entity.label === "car" && world.traffic.cars.has(entity.id))
    .map((car) => ({ x: car.x, y: car.y }));
  return { trees, cars };
}

export function step(world: World, dt = STEP): void {
  let suns = 0;
  let around: Surroundings | undefined;
  for (const entity of world.entities) {
    entity.age += dt;
    if (entity.label === "sun") {
      suns += 1;
    }
    if (entity.age <= SPAWN_SECONDS) {
      continue;
    }
    if (entity.drift !== 0) {
      entity.x = wrap(entity, entity.x + entity.drift * dt);
    }
    if (entity.label === "tree" || entity.label === "flower") {
      grow(world, entity, dt);
    }
    if (entity.label === "car" && !world.traffic.cars.has(entity.id)) {
      const { drawing, rest } = entity;
      addCar(world.traffic, entity.id, {
        x: rest.x,
        width: drawing.width * rest.scale,
        height: drawing.height * rest.scale,
        speed: entity.speed,
        facing: entity.facing,
      });
    }
    if (entity.cat) {
      around ??= surroundings(world);
      stepCat(entity.cat, entity, around, dt);
    }
  }
  drive(world, dt);
  const daylight = Math.min(1, suns * SUN_LIGHT);
  world.sunlight += (daylight - world.sunlight) * (1 - Math.exp(-dt / LIGHT_EASE_SECONDS));
}

function drive(world: World, dt: number): void {
  if (world.traffic.cars.size === 0) {
    return;
  }
  stepTraffic(world.traffic, dt);
  for (const entity of world.entities) {
    const car = world.traffic.cars.get(entity.id);
    if (car) {
      const now = carPose(car, dt);
      entity.x = now.x;
      entity.y = now.y;
      entity.facing = now.facing;
      entity.rotation = now.rotation;
    }
  }
}

/** The pose after settling, `t` world seconds in. */
function settledPose(entity: Entity, t: number): Pose {
  const { rest, phase } = entity;
  const mirror = entity.facing === entity.startFacing ? 1 : -1;
  const base: Pose = { x: rest.x, y: rest.y, scale: rest.scale, rotation: 0, mirror, glow: 0, bloom: 0, settled: 1 };
  switch (entity.label) {
    case "sun": {
      const wave = Math.sin((2 * Math.PI * t) / SUN_PERIOD_SECONDS + phase);
      return { ...base, scale: rest.scale * (1 + SUN_PULSE * wave), glow: SUN_GLOW + SUN_GLOW_PULSE * wave };
    }
    case "cloud": {
      const bob = CLOUD_BOB * Math.sin((2 * Math.PI * t) / CLOUD_BOB_SECONDS + phase);
      return { ...base, x: entity.x, y: rest.y + bob };
    }
    case "tree": {
      const { growth } = entity;
      const size = growth <= 1 ? SAPLING + (1 - SAPLING) * easeOutCubic(growth) : growth;
      return { ...base, scale: rest.scale * size };
    }
    case "flower": {
      const size = BUD + (1 - BUD) * easeOutCubic(entity.growth);
      const swell = 1 + BLOOM_SWELL * easeOutCubic(entity.bloom);
      const rotation = FLOWER_SWAY * Math.sin((2 * Math.PI * t) / FLOWER_SWAY_SECONDS + phase);
      return { ...base, scale: rest.scale * size * swell, rotation, bloom: entity.bloom };
    }
    case "car":
      return { ...base, x: entity.x, y: entity.y, rotation: entity.rotation };
    case "cat": {
      const cat = entity.cat!;
      const moving = cat.mood === "idle" ? 0 : 1;
      const rotation = 0.05 * moving * Math.sin(t * 9 + phase);
      return { ...base, x: entity.x, y: entity.y - hopHeight(cat), rotation };
    }
    default:
      return { ...base, rotation: SWAY * Math.sin((2 * Math.PI * t) / SWAY_SECONDS + phase) };
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
    mirror: resting.mirror,
    glow: resting.glow * t,
    bloom: resting.bloom,
    settled,
  };
}
