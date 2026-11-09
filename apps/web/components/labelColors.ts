import type { Label } from "../lib/contract";

/** Each class's color on the page, matched to the color it settles into in the world. */
export const LABEL_COLOR: Record<Label, string> = {
  sun: "text-sun",
  cloud: "text-sky",
  tree: "text-leaf",
  flower: "text-blossom",
  car: "text-[#3f6fa8]",
  cat: "text-[#8a6250]",
};
