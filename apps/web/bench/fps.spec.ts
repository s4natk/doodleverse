import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { expect, test, type CDPSession, type Page } from "@playwright/test";

import { shapes, type Stroke } from "../e2e/support";
import { LABELS, type Label } from "../lib/contract";
import type { Sketch } from "../lib/world/layout";
import type { WorldStats } from "../lib/world/scene";

/** Four of each class: about what a person places in a few minutes of drawing. */
const PER_CLASS = 4;
const SETTLE_MS = 3000;
const WINDOW_MS = 10_000;
const STROKE_WIDTH = 6;
const WEB = path.resolve(__dirname, "..");
const RESULTS = path.resolve(WEB, "..", "..", "bench", "results", "fps.json");

type Summary = { p50: number; p95: number; mean: number; max: number };

function percentile(sorted: number[], fraction: number): number {
  const rank = (sorted.length - 1) * fraction;
  const low = Math.floor(rank);
  const high = Math.ceil(rank);
  return sorted[low] + (sorted[high] - sorted[low]) * (rank - low);
}

/** Linear interpolation between ranks, like numpy's default and bench/api.py. */
function summarize(values: number[]): Summary {
  const sorted = [...values].sort((a, b) => a - b);
  return {
    p50: percentile(sorted, 0.5),
    p95: percentile(sorted, 0.95),
    mean: values.reduce((sum, value) => sum + value, 0) / values.length,
    max: sorted[sorted.length - 1],
  };
}

function rounded(value: unknown): unknown {
  if (typeof value === "number" && !Number.isInteger(value)) {
    return Math.round(value * 1000) / 1000;
  }
  if (Array.isArray(value)) {
    return value.map(rounded);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, rounded(item)]));
  }
  return value;
}

/** Strokes for the `index`-th drawing of a class, spread across a canvas of this size. */
function drawing(label: Label, index: number, { width, height }: { width: number; height: number }): Stroke[] {
  const x = width * (0.12 + 0.24 * index);
  switch (label) {
    case "sun":
      return shapes.sun(x, height * 0.16);
    case "cloud":
      return shapes.cloud(x - 60, height * 0.32);
    case "tree":
      return shapes.tree(x, height * 0.86);
    case "flower":
      return shapes.flower(x + 30, height * 0.9);
    case "car":
      return shapes.car(x - 55, height * 0.88);
    case "cat":
      return shapes.cat(x - 25, height * 0.86);
  }
}

function sketch(label: Label, strokes: Stroke[], canvas: { width: number; height: number }): Sketch {
  const points = strokes.flat();
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  return {
    label,
    strokes: strokes.map((stroke) => ({ points: stroke, width: STROKE_WIDTH })),
    bounds: { minX: Math.min(...xs), minY: Math.min(...ys), maxX: Math.max(...xs), maxY: Math.max(...ys) },
    canvas,
  };
}

async function mainThread(cdp: CDPSession): Promise<{ at: number; task: number; script: number }> {
  const { metrics } = await cdp.send("Performance.getMetrics");
  const value = (name: string) => metrics.find((metric) => metric.name === name)?.value ?? 0;
  return { at: value("Timestamp"), task: value("TaskDuration"), script: value("ScriptDuration") };
}

/** Frame intervals from requestAnimationFrame, and how much of the window the main thread spent busy. */
async function measure(page: Page, cdp: CDPSession) {
  const before = await mainThread(cdp);
  const stamps = await page.evaluate(
    (windowMs) =>
      new Promise<number[]>((resolve) => {
        const times: number[] = [];
        const frame = (now: number) => {
          times.push(now);
          if (now - times[0] < windowMs) {
            requestAnimationFrame(frame);
          } else {
            resolve(times);
          }
        };
        requestAnimationFrame(frame);
      }),
    WINDOW_MS,
  );
  const after = await mainThread(cdp);
  const intervals = stamps.slice(1).map((time, index) => time - stamps[index]);
  const seconds = (stamps[stamps.length - 1] - stamps[0]) / 1000;
  const elapsed = after.at - before.at;
  return {
    seconds,
    frames: intervals.length,
    fps: intervals.length / seconds,
    frame_ms: summarize(intervals),
    main_thread_busy: (after.task - before.task) / elapsed,
    script_busy: (after.script - before.script) / elapsed,
  };
}

function stats(page: Page): Promise<WorldStats> {
  return page.evaluate(() => window.__doodleverseWorld!.stats());
}

function git(...args: string[]): string {
  return execFileSync("git", args, { cwd: WEB, encoding: "utf8" }).trim();
}

function installed(name: string): string {
  return JSON.parse(readFileSync(path.join(WEB, "node_modules", name, "package.json"), "utf8")).version;
}

function localDate(): string {
  const now = new Date();
  return [now.getFullYear(), now.getMonth() + 1, now.getDate()].map((part) => String(part).padStart(2, "0")).join("-");
}

test("frames per second, empty and with four of each class", async ({ page, browser, browserName }) => {
  await page.goto("/");
  await page.waitForFunction(() => window.__doodleverseWorld !== undefined);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Performance.enable");
  const box = await page.getByLabel("Drawing area").boundingBox();
  expect(box).not.toBeNull();
  const canvas = { width: box!.width, height: box!.height };

  await page.waitForTimeout(SETTLE_MS);
  const empty = await measure(page, cdp);

  const sketches = LABELS.flatMap((label) =>
    Array.from({ length: PER_CLASS }, (_, index) => sketch(label, drawing(label, index, canvas), canvas)),
  );
  await page.evaluate((all) => all.forEach((one) => window.__doodleverseWorld!.spawn(one)), sketches);
  // Clouds take taps once they settle, and start drifting into each other soon after.
  await page.waitForTimeout(800);
  await page.evaluate(() => {
    const world = window.__doodleverseWorld!;
    for (const cloud of world.stats().clouds) {
      world.tap(cloud.x, cloud.y);
    }
  });
  await page.waitForTimeout(SETTLE_MS);
  const busy = await stats(page);
  expect(busy).toMatchObject({ entities: LABELS.length * PER_CLASS, raining: PER_CLASS, bodies: 3 + PER_CLASS });
  const full = await measure(page, cdp);

  const environment = await page.evaluate(() => {
    const probe = document.createElement("canvas").getContext("webgl2");
    const debug = probe?.getExtension("WEBGL_debug_renderer_info");
    const gpu = probe ? String(probe.getParameter(debug ? debug.UNMASKED_RENDERER_WEBGL : probe.RENDERER)) : null;
    probe?.getExtension("WEBGL_lose_context")?.loseContext();
    const world = document.querySelector<HTMLCanvasElement>("[aria-label='World'] canvas");
    return {
      headless: navigator.userAgent.includes("HeadlessChrome"),
      gpu,
      viewport: [window.innerWidth, window.innerHeight],
      device_pixel_ratio: window.devicePixelRatio,
      world_canvas: world ? [world.width, world.height] : null,
      reduced_motion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    };
  });
  const { headless, gpu, ...shown } = environment;
  const cpus = os.cpus();
  const results = {
    benchmark: "fps",
    date: localDate(),
    git: {
      commit: git("rev-parse", "HEAD"),
      dirty: git("status", "--porcelain", "--", ":/", ":(top,exclude)bench/results").length > 0,
    },
    machine: {
      os: `${os.version()} ${os.release()}`,
      cpu: cpus[0]?.model.trim() ?? os.arch(),
      logical_cpus: cpus.length,
      memory_gib: Math.round((os.totalmem() / 2 ** 30) * 10) / 10,
    },
    browser: { name: browserName, version: browser.version(), headless, gpu, renderer: busy.renderer },
    page: shown,
    versions: {
      node: process.versions.node,
      ...Object.fromEntries(["next", "react", "pixi.js", "matter-js", "@playwright/test"].map((name) => [name, installed(name)])),
    },
    method:
      `${SETTLE_MS / 1000} s to settle, then ${WINDOW_MS / 1000} s of requestAnimationFrame timestamps. ` +
      "Entities are spawned through the scene, not drawn, and every cloud is raining.",
    runs: [
      { entities: 0, ...empty },
      { entities: busy.entities, per_class: PER_CLASS, raining_clouds: busy.raining, physics_bodies: busy.bodies, ...full },
    ],
  };
  mkdirSync(path.dirname(RESULTS), { recursive: true });
  writeFileSync(RESULTS, JSON.stringify(rounded(results), null, 2) + "\n");
  for (const run of results.runs) {
    console.log(
      `${String(run.entities).padStart(2)} entities: ${run.fps.toFixed(1)} fps, frame p50 ${run.frame_ms.p50.toFixed(2)} ms ` +
        `p95 ${run.frame_ms.p95.toFixed(2)} ms max ${run.frame_ms.max.toFixed(1)} ms, ` +
        `main thread busy ${(run.main_thread_busy * 100).toFixed(1)}%`,
    );
  }
  console.log(`${gpu ?? "no WebGL"}; ${headless ? "headless" : "headed"} ${browserName} ${browser.version()}`);
});
