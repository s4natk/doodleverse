import { describe, expect, it } from "vitest";

import { STEP } from "./clock";
import { addCar, bodyCount, createTraffic, destroyTraffic, physicsListeners } from "./cars";

describe("traffic", () => {
  it("starts with a collision listener and three static bodies", () => {
    const traffic = createTraffic(STEP);
    expect(physicsListeners(traffic.engine)).toBe(1);
    expect(bodyCount(traffic)).toBe(3);
  });

  it("drops the listener and every body when torn down", () => {
    const traffic = createTraffic(STEP);
    addCar(traffic, 1, { x: 300, width: 80, height: 40, speed: 50, facing: 1 });
    expect(bodyCount(traffic)).toBe(4);
    destroyTraffic(traffic);
    expect(physicsListeners(traffic.engine)).toBe(0);
    expect(bodyCount(traffic)).toBe(0);
  });
});
