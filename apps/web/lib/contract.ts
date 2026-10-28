// Must match ml/doodleverse/classes.py and ml/doodleverse/preprocess/validate.py. contract.test.ts reads both.
export const LABELS = ["sun", "cloud", "tree", "flower", "car", "cat"] as const;
export type Label = (typeof LABELS)[number];

export const MAX_STROKES = 64;
export const MAX_POINTS = 4096;
export const MAX_CANVAS = 8192;

export function isLabel(value: unknown): value is Label {
  return typeof value === "string" && (LABELS as readonly string[]).includes(value);
}
