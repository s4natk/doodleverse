import Matter from "matter-js";

import { ROAD_Y, WORLD_WIDTH } from "./layout";
import { CAR_HOP, CAR_MAX_TILT, CAR_TILT } from "./rules";

const { Bodies, Body, Composite, Engine, Events } = Matter;

export type Car = {
  body: Matter.Body;
  /** 1 drives right, -1 drives left. */
  facing: number;
  /** World units per second. */
  speed: number;
  halfHeight: number;
};

/** One Matter.js engine for every car: the road, a wall at each edge, and a body per car. */
export type Traffic = {
  engine: Matter.Engine;
  /** By entity id. */
  cars: Map<number, Car>;
  byBody: Map<number, Car>;
};

const SLAB = 100;

/** Matter velocities are per step, so speeds in world units per second are scaled by `step`. */
function bump(car: Car, awayFrom: number, step: number): void {
  car.facing = car.body.position.x >= awayFrom ? 1 : -1;
  Body.setVelocity(car.body, { x: car.body.velocity.x, y: -CAR_HOP * step });
}

export function createTraffic(step: number): Traffic {
  const engine = Engine.create({ gravity: { x: 0, y: 1 } });
  const road = Bodies.rectangle(WORLD_WIDTH / 2, ROAD_Y + SLAB / 2, WORLD_WIDTH * 3, SLAB, {
    isStatic: true,
    label: "road",
  });
  const left = Bodies.rectangle(-SLAB / 2, ROAD_Y - 300, SLAB, 600, { isStatic: true, label: "wall" });
  const right = Bodies.rectangle(WORLD_WIDTH + SLAB / 2, ROAD_Y - 300, SLAB, 600, { isStatic: true, label: "wall" });
  Composite.add(engine.world, [road, left, right]);
  const traffic: Traffic = { engine, cars: new Map(), byBody: new Map() };
  Events.on(engine, "collisionStart", (event) => {
    for (const { bodyA, bodyB } of event.pairs) {
      for (const [self, other] of [
        [bodyA, bodyB],
        [bodyB, bodyA],
      ]) {
        const car = traffic.byBody.get(self.id);
        if (car && other.label !== "road") {
          bump(car, other.position.x, step);
        }
      }
    }
  });
  return traffic;
}

type NewCar = { x: number; width: number; height: number; speed: number; facing: number };

/** A body the size of the settled drawing, standing on the road. */
export function addCar(traffic: Traffic, id: number, { x, width, height, speed, facing }: NewCar): Car {
  const w = Math.max(width, 24);
  const h = Math.max(height, 16);
  const body = Bodies.rectangle(x, ROAD_Y - h / 2, w, h, { friction: 0, frictionAir: 0, restitution: 0, label: "car" });
  Body.setInertia(body, Infinity);
  Composite.add(traffic.engine.world, body);
  const car = { body, facing, speed, halfHeight: h / 2 };
  traffic.cars.set(id, car);
  traffic.byBody.set(body.id, car);
  return car;
}

export function removeCars(traffic: Traffic): void {
  for (const car of traffic.cars.values()) {
    Composite.remove(traffic.engine.world, car.body);
  }
  traffic.cars.clear();
  traffic.byBody.clear();
}

/** How many Matter callbacks are still hanging off the engine. */
export function physicsListeners(engine: Matter.Engine): number {
  const events = (engine as Matter.Engine & { events?: Record<string, unknown[] | undefined> }).events;
  if (!events) {
    return 0;
  }
  return Object.values(events).reduce((sum, list) => sum + (Array.isArray(list) ? list.length : 0), 0);
}

/** Every body in the world, including the road and the walls. */
export function bodyCount(traffic: Traffic): number {
  return Composite.allBodies(traffic.engine.world).length;
}

/** Drop the cars, the statics, and the collision callback. The engine is not reused after this. */
export function destroyTraffic(traffic: Traffic): void {
  Events.off(traffic.engine, "collisionStart");
  Composite.clear(traffic.engine.world, false);
  traffic.cars.clear();
  traffic.byBody.clear();
  Engine.clear(traffic.engine);
}

/** Hold every car at its cruising speed, then let Matter move them and sort out the bumps. */
export function stepTraffic(traffic: Traffic, step: number, motion: number): void {
  for (const car of traffic.cars.values()) {
    Body.setVelocity(car.body, { x: car.facing * car.speed * motion * step, y: car.body.velocity.y });
  }
  Engine.update(traffic.engine, step * 1000);
}

/** Where the car's drawing stands: the base of its body, which way it faces, and its nose-up tilt. */
export function carPose(car: Car, step: number): { x: number; y: number; facing: number; rotation: number } {
  const rising = -car.body.velocity.y / step;
  const tilt = Math.max(-CAR_MAX_TILT, Math.min(CAR_MAX_TILT, rising * CAR_TILT));
  return {
    x: car.body.position.x,
    y: car.body.position.y + car.halfHeight,
    facing: car.facing,
    rotation: -tilt * car.facing,
  };
}
