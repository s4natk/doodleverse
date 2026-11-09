import type { CSSProperties } from "react";

/** When a draw-in starts and how long it takes, read by the animation classes in globals.css. */
export function at(delay: number, duration?: number): CSSProperties {
  return { "--d": `${delay}s`, ...(duration ? { "--t": `${duration}s` } : {}) } as CSSProperties;
}
