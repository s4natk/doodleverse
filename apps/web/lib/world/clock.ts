/** World time advances in fixed steps, however long each frame took. */
export const STEP = 1 / 60;
// A longer frame (a background tab, a breakpoint) counts as this long instead of being replayed.
export const MAX_FRAME = 0.25;
/** Enough for a whole MAX_FRAME at the fastest speed. Anything owed beyond it is dropped. */
export const MAX_SPEED = 2;
export const MAX_STEPS = Math.round((MAX_FRAME * MAX_SPEED) / STEP);

export type Clock = {
  /** World seconds owed to the simulation, less than one step after `advance`. */
  owed: number;
  speed: number;
  paused: boolean;
  /** World seconds simulated so far. */
  time: number;
};

export function createClock(): Clock {
  return { owed: 0, speed: 1, paused: false, time: 0 };
}

/** Add one frame's real milliseconds and return how many fixed steps to run for it. */
export function advance(clock: Clock, elapsedMs: number): number {
  if (clock.paused || !(elapsedMs > 0)) {
    return 0;
  }
  clock.owed += Math.min(elapsedMs / 1000, MAX_FRAME) * clock.speed;
  let steps = Math.floor(clock.owed / STEP);
  if (steps > MAX_STEPS) {
    steps = MAX_STEPS;
    clock.owed = 0;
  } else {
    clock.owed -= steps * STEP;
  }
  clock.time += steps * STEP;
  return steps;
}
