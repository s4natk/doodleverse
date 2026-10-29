import type { Label } from "../contract";

/** The ink a drawing has on the sketch layer, before it settles into the world. */
export const INK = 0x2c2733;

export const STROKE: Record<Label, number> = {
  sun: 0xf0a23a,
  cloud: 0xffffff,
  tree: 0x4a7d45,
  flower: 0xc2588a,
  car: 0x3f6fa8,
  cat: 0x7a5747,
};

export const CLOUD_OUTLINE = 0x8fa7bf;

/** Sky and ground with no sun, then in full daylight. */
export const DUSK = { skyTop: 0x5d6a86, skyHorizon: 0xa898a6, ground: 0x5f6e52, groundEdge: 0x4f5c45 };
export const DAY = { skyTop: 0x8fcbea, skyHorizon: 0xfbe3b8, ground: 0x9cc472, groundEdge: 0x7fa95a };

/** Everything on the ground and in the sky is multiplied by this, from dusk to day. */
export const SHADE_AT_DUSK = 0x9ea2ba;

function channel(color: number, shift: number): number {
  return (color >> shift) & 0xff;
}

export function mixColor(from: number, to: number, t: number): number {
  const amount = Math.min(1, Math.max(0, t));
  let mixed = 0;
  for (const shift of [16, 8, 0]) {
    const value = Math.round(channel(from, shift) + (channel(to, shift) - channel(from, shift)) * amount);
    mixed |= value << shift;
  }
  return mixed;
}
