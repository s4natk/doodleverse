import { describe, expect, it } from "vitest";

import { nextStep, readStep, saveStep, STORAGE_KEY } from "./onboarding";

function memory(): Storage {
  const items = new Map<string, string>();
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => void items.set(key, value),
    removeItem: (key) => void items.delete(key),
    clear: () => items.clear(),
    key: (index) => [...items.keys()][index] ?? null,
    get length() {
      return items.size;
    },
  };
}

describe("first-use prompt", () => {
  it("asks for a sun, then a cloud, then anything, then stops", () => {
    expect(nextStep("sun", "tree")).toBe("sun");
    expect(nextStep("sun", "sun")).toBe("cloud");
    expect(nextStep("cloud", "sun")).toBe("cloud");
    expect(nextStep("cloud", "cloud")).toBe("anything");
    expect(nextStep("anything", "cat")).toBe("done");
    expect(nextStep("done", "sun")).toBe("done");
  });

  it("remembers only that it finished", () => {
    const storage = memory();
    expect(readStep(storage)).toBe("sun");
    saveStep(storage, "cloud");
    expect(storage.getItem(STORAGE_KEY)).toBeNull();
    saveStep(storage, "done");
    expect(readStep(storage)).toBe("done");
    saveStep(storage, "sun");
    expect(readStep(storage)).toBe("sun");
  });

  it("shows the prompt when storage is missing or refuses", () => {
    const refusing = { ...memory(), getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
    expect(readStep(null)).toBe("sun");
    expect(readStep(refusing)).toBe("sun");
    expect(() => saveStep(refusing, "done")).not.toThrow();
  });
});
