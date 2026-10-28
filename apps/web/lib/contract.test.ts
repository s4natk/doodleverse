import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { isLabel, LABELS, MAX_CANVAS, MAX_POINTS, MAX_STROKES } from "./contract";

function python(path: string): string {
  return readFileSync(new URL(`../../../ml/doodleverse/${path}`, import.meta.url), "utf8");
}

describe("contract with the Python side", () => {
  it("lists the labels in the model's softmax order", () => {
    const tuple = python("classes.py").match(/^LABELS[^=]*=\s*\(([^)]*)\)/m);
    expect(tuple).not.toBeNull();
    const labels = [...tuple![1].matchAll(/"([^"]+)"/g)].map((match) => match[1]);
    expect([...LABELS]).toEqual(labels);
  });

  it("uses the sketch limits the validator enforces", () => {
    const source = python("preprocess/validate.py");
    const read = (name: string) => Number(source.match(new RegExp(`^${name} = ([\\d_]+)`, "m"))?.[1].replaceAll("_", ""));
    expect({ MAX_STROKES, MAX_POINTS, MAX_CANVAS }).toEqual({
      MAX_STROKES: read("MAX_STROKES"),
      MAX_POINTS: read("MAX_POINTS"),
      MAX_CANVAS: read("MAX_CANVAS"),
    });
  });

  it("accepts only the six labels", () => {
    expect(LABELS.every(isLabel)).toBe(true);
    expect(isLabel("dog")).toBe(false);
    expect(isLabel(3)).toBe(false);
  });
});
