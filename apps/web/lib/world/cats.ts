import { clamp, GROUND_Y, WORLD_WIDTH } from "./layout";
import { unit } from "./random";
import {
  CAT_CALM_SECONDS,
  CAT_FLEE_DISTANCE,
  CAT_FLEE_SECONDS,
  CAT_FLEE_SPEED,
  CAT_HOP_HEIGHT,
  CAT_HOP_SECONDS,
  CAT_IDLE_MIN,
  CAT_IDLE_RANGE,
  CAT_LOOKAHEAD,
  CAT_RADIUS,
  CAT_REACT_DISTANCE,
  CAT_WALK_SPEED,
} from "./rules";

export type Mood = "idle" | "walk" | "flee";

export type CatState = {
  mood: Mood;
  /** World seconds left in this mood. */
  timer: number;
  target: { x: number; y: number };
  /** Seconds into a startled hop, or -1 when on the ground. */
  hop: number;
  /** Seconds before a car can startle it again. */
  calm: number;
  /** Walks taken so far, which picks the next spot. */
  walks: number;
};

/** A trunk footprint on the ground plane. */
export type Obstacle = { x: number; y: number; r: number };

export type Surroundings = { trees: Obstacle[]; cars: { x: number; y: number }[] };

type Body = { id: number; x: number; y: number; facing: number };

/** The strip of ground cats walk on: the top of the grass to near the bottom edge. */
export const PATH_TOP = GROUND_Y + 2;
export const PATH_BOTTOM = GROUND_Y + 78;
const MARGIN = 50;
const ARRIVED = 6;
const MAX_WALK_SECONDS = 15;

function idleFor(id: number, walks: number): number {
  return CAT_IDLE_MIN + CAT_IDLE_RANGE * unit(id, 40 + walks);
}

export function createCat(id: number): CatState {
  return { mood: "idle", timer: idleFor(id, 0), target: { x: 0, y: 0 }, hop: -1, calm: 0, walks: 0 };
}

function clear(point: { x: number; y: number }, trees: Obstacle[]): boolean {
  return trees.every((tree) => Math.hypot(point.x - tree.x, point.y - tree.y) > tree.r + CAT_RADIUS);
}

/** A spot on the path away from any trunk. Tries a few seeded spots, then takes the last one. */
function nextSpot(id: number, walks: number, trees: Obstacle[]): { x: number; y: number } {
  let spot = { x: 0, y: 0 };
  for (let attempt = 0; attempt < 6; attempt += 1) {
    spot = {
      x: MARGIN + (WORLD_WIDTH - 2 * MARGIN) * unit(id, 60 + walks * 7 + attempt),
      y: PATH_TOP + (PATH_BOTTOM - PATH_TOP) * unit(id, 80 + walks * 7 + attempt),
    };
    if (clear(spot, trees)) {
      break;
    }
  }
  return spot;
}

/** Head for the target at `speed`, bending sideways around any trunk within the lookahead. */
export function steer(from: { x: number; y: number }, to: { x: number; y: number }, speed: number, trees: Obstacle[]) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.hypot(dx, dy);
  if (distance < 1e-6 || speed === 0) {
    return { vx: 0, vy: 0 };
  }
  const ux = dx / distance;
  const uy = dy / distance;
  let vx = ux;
  let vy = uy;
  for (const tree of trees) {
    const ox = tree.x - from.x;
    const oy = tree.y - from.y;
    const ahead = ox * ux + oy * uy;
    if (ahead <= 0 || ahead > CAT_LOOKAHEAD + tree.r || ahead > distance + tree.r) {
      continue;
    }
    const sideX = ox - ux * ahead;
    const sideY = oy - uy * ahead;
    const side = Math.hypot(sideX, sideY);
    const room = tree.r + CAT_RADIUS;
    if (side >= room) {
      continue;
    }
    // Push away from the trunk. Dead ahead, go round on whichever side has more path left.
    const awayX = side > 1e-6 ? -sideX / side : 0;
    const awayY = side > 1e-6 ? -sideY / side : from.y - PATH_TOP > PATH_BOTTOM - from.y ? -1 : 1;
    const push = (2 * (room - side)) / room;
    vx += awayX * push;
    vy += awayY * push;
  }
  const length = Math.hypot(vx, vy) || 1;
  return { vx: (vx / length) * speed, vy: (vy / length) * speed };
}

function nearestCar(body: Body, cars: Surroundings["cars"]): { x: number; y: number } | null {
  let nearest: { x: number; y: number } | null = null;
  for (const car of cars) {
    if (Math.abs(car.x - body.x) < CAT_REACT_DISTANCE && Math.abs(car.y - body.y) < 60) {
      if (!nearest || Math.abs(car.x - body.x) < Math.abs(nearest.x - body.x)) {
        nearest = car;
      }
    }
  }
  return nearest;
}

export function stepCat(cat: CatState, body: Body, around: Surroundings, dt: number): void {
  cat.calm = Math.max(0, cat.calm - dt);
  if (cat.hop >= 0) {
    cat.hop = cat.hop + dt > CAT_HOP_SECONDS ? -1 : cat.hop + dt;
  }
  const car = cat.mood === "flee" || cat.calm > 0 ? null : nearestCar(body, around.cars);
  if (car) {
    const away = body.x >= car.x ? 1 : -1;
    cat.mood = "flee";
    cat.timer = CAT_FLEE_SECONDS;
    cat.hop = 0;
    cat.target = { x: clamp(body.x + away * CAT_FLEE_DISTANCE, MARGIN, WORLD_WIDTH - MARGIN), y: body.y };
  }
  cat.timer -= dt;
  if (cat.mood === "idle") {
    if (cat.timer <= 0) {
      cat.walks += 1;
      cat.mood = "walk";
      cat.timer = MAX_WALK_SECONDS;
      cat.target = nextSpot(body.id, cat.walks, around.trees);
    }
    return;
  }
  const speed = cat.mood === "flee" ? CAT_FLEE_SPEED : CAT_WALK_SPEED;
  const { vx, vy } = steer(body, cat.target, speed, around.trees);
  body.x = clamp(body.x + vx * dt, MARGIN / 2, WORLD_WIDTH - MARGIN / 2);
  body.y = clamp(body.y + vy * dt, PATH_TOP, PATH_BOTTOM);
  if (Math.abs(vx) > 1) {
    body.facing = vx > 0 ? 1 : -1;
  }
  const arrived = Math.hypot(cat.target.x - body.x, cat.target.y - body.y) < ARRIVED;
  if (arrived || cat.timer <= 0) {
    if (cat.mood === "flee") {
      cat.calm = CAT_CALM_SECONDS;
    }
    cat.mood = "idle";
    cat.timer = idleFor(body.id, cat.walks);
  }
}

/** How high a startled cat is off the ground right now. */
export function hopHeight(cat: CatState): number {
  return cat.hop < 0 ? 0 : CAT_HOP_HEIGHT * Math.sin((Math.PI * cat.hop) / CAT_HOP_SECONDS);
}
