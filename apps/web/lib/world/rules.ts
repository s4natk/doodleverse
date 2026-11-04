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
/** A tap this close to a cloud's drawing still counts as a tap on it. */
export const TAP_SLOP = 16;

/** Rain falls from the middle of a cloud, this fraction of its width. */
export const RAIN_WIDTH = 0.8;
/** Water a flower soaks up per second of rain, out of 1. */
export const RAIN_WATER = 0.5;
/** A tree in the rain grows this many times faster, */
export const RAIN_GROWTH = 4;
/** and keeps going past its usual size up to this. */
export const RAIN_MAX_GROWTH = 1.25;

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

/** Cars drive between these speeds, fixed per car. */
export const CAR_SPEED_MIN = 40;
export const CAR_SPEED_RANGE = 30;
/** Upward speed a car gets when it bumps into something. */
export const CAR_HOP = 150;
/** A car's nose tips up this much per unit of upward speed, at most CAR_MAX_TILT radians. */
export const CAR_TILT = 0.0008;
export const CAR_MAX_TILT = 0.15;

export const CAT_WALK_SPEED = 45;
export const CAT_FLEE_SPEED = 140;
/** A cat sits still for CAT_IDLE_MIN to CAT_IDLE_MIN + CAT_IDLE_RANGE seconds between walks. */
export const CAT_IDLE_MIN = 1.5;
export const CAT_IDLE_RANGE = 3;
/** A car closer than this, along the ground, startles a cat. */
export const CAT_REACT_DISTANCE = 140;
export const CAT_HOP_SECONDS = 0.35;
export const CAT_HOP_HEIGHT = 26;
export const CAT_FLEE_DISTANCE = 220;
export const CAT_FLEE_SECONDS = 1.6;
/** After running off, a cat ignores cars for this long. */
export const CAT_CALM_SECONDS = 2;
/** A cat's footprint, kept clear of tree trunks. */
export const CAT_RADIUS = 12;
/**
 * A tree's trunk footprint as a fraction of its width, at least TRUNK_MIN. Small enough that a
 * trunk anywhere on the 80-unit-deep ground still leaves a way round on one side.
 */
export const TRUNK_FRACTION = 0.08;
export const TRUNK_MIN = 8;
/** How far ahead a walking cat looks for trees in its way. */
export const CAT_LOOKAHEAD = 90;

/** Gentle rocking, in radians, for things with no behavior of their own. */
export const SWAY = 0.03;
export const SWAY_SECONDS = 3;
