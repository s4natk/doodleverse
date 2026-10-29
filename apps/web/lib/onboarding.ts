import type { Label } from "./contract";

/** A first visit asks for a sun, then a cloud, then lets the person draw anything. */
export type FirstUse = "sun" | "cloud" | "anything" | "done";

export const PROMPTS: Record<Exclude<FirstUse, "done">, string> = {
  sun: "Start with a sun.",
  cloud: "Now a cloud for the sky.",
  anything: "Now anything: a tree, a flower, a car, or a cat.",
};

export const STORAGE_KEY = "doodleverse.firstUse";

export function nextStep(step: FirstUse, placed: Label): FirstUse {
  switch (step) {
    case "sun":
      return placed === "sun" ? "cloud" : "sun";
    case "cloud":
      return placed === "cloud" ? "anything" : "cloud";
    default:
      return "done";
  }
}

type Store = Pick<Storage, "getItem" | "setItem" | "removeItem">;

// Storage can be missing or throw (private windows, blocked cookies). The prompt then shows every visit.
export function readStep(storage: Store | null): FirstUse {
  try {
    return storage?.getItem(STORAGE_KEY) === "done" ? "done" : "sun";
  } catch {
    return "sun";
  }
}

export function saveStep(storage: Store | null, step: FirstUse): void {
  try {
    if (step === "done") {
      storage?.setItem(STORAGE_KEY, "done");
    } else if (step === "sun") {
      storage?.removeItem(STORAGE_KEY);
    }
  } catch {
    // Nothing to do: the walkthrough will show again next time.
  }
}
