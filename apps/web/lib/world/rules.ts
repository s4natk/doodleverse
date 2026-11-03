/**
 * Every number that shapes how things behave in the world. Distances are world units
 * (the world is 960 × 720), times are world seconds, rates are per world second.
 */

/** A confirmed drawing takes this long to move from where it was drawn to where it settles. */
export const SPAWN_SECONDS = 0.6;

export const SUN_PERIOD_SECONDS = 4;
/** How far the sun's size swings each way, as a fraction. */
export const SUN_PULSE = 0.05;
export const SUN_GLOW = 0.6;
export const SUN_GLOW_PULSE = 0.2;
/** Daylight one sun brings, out of 1. Two or more bring full day. */
export const SUN_LIGHT = 0.85;
export const LIGHT_EASE_SECONDS = 1.2;

export const CLOUD_DRIFT_MIN = 12;
export const CLOUD_DRIFT_RANGE = 14;
export const CLOUD_BOB = 4;
export const CLOUD_BOB_SECONDS = 6;

export const TREE_GROW_SECONDS = 12;
/** A new tree starts at this fraction of its grown size. */
export const SAPLING = 0.35;

export const FLOWER_GROW_SECONDS = 6;
/** A new flower starts at this fraction of its grown size. */
export const BUD = 0.5;
export const FLOWER_SWAY = 0.06;
export const FLOWER_SWAY_SECONDS = 2.4;
/** A flower opens only with at least this much daylight and this much water in it. */
export const BLOOM_LIGHT = 0.5;
export const BLOOM_WATER = 0.25;
export const BLOOM_SECONDS = 1.5;
/** Closing again takes this long once the light is gone. */
export const WILT_SECONDS = 10;
/** A soaked flower dries out over this long. */
export const DRY_SECONDS = 40;
/** An open flower is this much bigger than a closed one. */
export const BLOOM_SWELL = 0.2;

/** Gentle rocking, in radians, for things with no behavior of their own. */
export const SWAY = 0.03;
export const SWAY_SECONDS = 3;
