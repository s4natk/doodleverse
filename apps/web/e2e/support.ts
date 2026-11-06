import { expect, type Page, type Route } from "@playwright/test";

import { WORLD_HEIGHT, WORLD_WIDTH } from "../lib/world/layout";

export type Point = [number, number];
export type Stroke = Point[];

export const API = "http://api.test/predict";

type Guess = { label: string; score: number };

/** A /predict answer in the service's shape. */
export function answer(label: string, options: { uncertain?: boolean; top3?: Guess[] } = {}) {
  const top3 = options.top3 ?? [
    { label, score: 0.97 },
    { label: label === "cat" ? "sun" : "cat", score: 0.02 },
    { label: label === "tree" ? "flower" : "tree", score: 0.01 },
  ];
  return {
    label: top3[0].label,
    score: top3[0].score,
    top3,
    uncertain: options.uncertain ?? false,
    model_version: "gap-e2e",
    latency_ms: 2,
  };
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export type Reply = { status?: number; body: unknown } | "offline";

/**
 * Stand in for the inference service. `reply` sees each request body, in order, and says what to send back.
 * Returns the bodies the page sent.
 */
export async function serve(page: Page, reply: (body: unknown, index: number) => Reply): Promise<unknown[]> {
  const received: unknown[] = [];
  await page.route(API, async (route: Route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS });
      return;
    }
    const body = request.postDataJSON();
    received.push(body);
    const next = reply(body, received.length - 1);
    if (next === "offline") {
      await route.abort("internetdisconnected");
      return;
    }
    await route.fulfill({
      status: next.status ?? 200,
      headers: CORS,
      contentType: "application/json",
      body: JSON.stringify(next.body),
    });
  });
  return received;
}

/** Draw strokes on the sketch layer with the real mouse, in canvas pixels. One move per point. */
export async function draw(page: Page, strokes: Stroke[]): Promise<void> {
  const box = await page.getByLabel("Drawing area").boundingBox();
  if (!box) {
    throw new Error("The drawing area is not on screen.");
  }
  for (const stroke of strokes) {
    const [first, ...rest] = stroke;
    await page.mouse.move(box.x + first[0], box.y + first[1]);
    await page.mouse.down();
    for (const [x, y] of rest) {
      await page.mouse.move(box.x + x, box.y + y);
    }
    await page.mouse.up();
  }
}

/** A quick click on the sketch layer, in canvas pixels. */
export async function tap(page: Page, [x, y]: Point): Promise<void> {
  const box = await page.getByLabel("Drawing area").boundingBox();
  if (!box) {
    throw new Error("The drawing area is not on screen.");
  }
  await page.mouse.click(box.x + x, box.y + y);
}

function ring(cx: number, cy: number, r: number, n = 24): Stroke {
  return Array.from({ length: n + 1 }, (_, i): Point => {
    const angle = (2 * Math.PI * i) / n;
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  });
}

/** Simple drawings, positioned in canvas pixels. */
export const shapes = {
  sun(cx: number, cy: number): Stroke[] {
    const rays = Array.from({ length: 8 }, (_, k): Stroke => {
      const angle = (2 * Math.PI * k) / 8;
      return [
        [cx + 44 * Math.cos(angle), cy + 44 * Math.sin(angle)],
        [cx + 66 * Math.cos(angle), cy + 66 * Math.sin(angle)],
      ];
    });
    return [ring(cx, cy, 32), ...rays];
  },
  cloud(x: number, y: number): Stroke[] {
    return [[[x, y], [x + 20, y - 30], [x + 55, y - 40], [x + 90, y - 30], [x + 120, y], [x + 120, y + 20], [x, y + 20], [x, y]]];
  },
  tree(x: number, base: number): Stroke[] {
    return [[[x - 6, base], [x - 6, base - 50]], [[x + 6, base], [x + 6, base - 50]], ring(x, base - 85, 36)];
  },
  car(x: number, y: number): Stroke[] {
    return [
      [[x, y], [x + 110, y], [x + 110, y - 30], [x + 75, y - 30], [x + 60, y - 55], [x + 25, y - 55], [x + 10, y - 30], [x, y - 30], [x, y]],
      ring(x + 25, y + 8, 11, 16),
      ring(x + 85, y + 8, 11, 16),
    ];
  },
  flower(x: number, base: number): Stroke[] {
    const petals = Array.from({ length: 6 }, (_, k): Stroke => {
      const angle = (2 * Math.PI * k) / 6;
      return ring(x + 16 * Math.cos(angle), base - 70 + 16 * Math.sin(angle), 10, 12);
    });
    return [[[x, base], [x, base - 55]], ring(x, base - 70, 9, 12), ...petals];
  },
  cat(x: number, base: number): Stroke[] {
    return [
      ring(x, base - 24, 24),
      ring(x + 30, base - 58, 16),
      [[x + 18, base - 68], [x + 20, base - 84], [x + 28, base - 73]],
      [[x + 34, base - 73], [x + 42, base - 84], [x + 44, base - 66]],
      [[x - 24, base - 24], [x - 40, base - 44], [x - 36, base - 62]],
    ];
  },
  line(x: number, y: number): Stroke[] {
    return [[[x, y], [x + 60, y + 20], [x + 120, y]]];
  },
};

/** Draw, ask, and accept the mock's top guess. */
export async function confirm(page: Page, label: string, strokes: Stroke[]): Promise<void> {
  await draw(page, strokes);
  await page.getByRole("button", { name: "Recognize" }).click();
  const yes = page.getByRole("button", { name: `Yes, it's a ${label}` });
  await expect(yes).toBeVisible();
  await yes.click();
}

export type WorldStats = {
  renderer: string;
  entities: number;
  views: number;
  displayObjects: number;
  bodies: number;
  tickerListeners: number;
  physicsListeners: number;
  motionListeners: number;
  raining: number;
  clouds: { x: number; y: number; raining: boolean; settled: boolean }[];
};

type WorldProbe = { stats(): WorldStats; destroy(): void };

/** The world's own counts, from the hook an E2E build exposes. */
export async function worldStats(page: Page): Promise<WorldStats> {
  await page.waitForFunction(() => "__doodleverseWorld" in window);
  return page.evaluate(() => (window as unknown as { __doodleverseWorld: WorldProbe }).__doodleverseWorld.stats());
}

/** A click at a world-space point, through the sketch layer that sits over it. */
export async function tapWorld(page: Page, [x, y]: Point): Promise<void> {
  const box = await page.getByLabel("Drawing area").boundingBox();
  if (!box) {
    throw new Error("The drawing area is not on screen.");
  }
  await page.mouse.click(box.x + (x / WORLD_WIDTH) * box.width, box.y + (y / WORLD_HEIGHT) * box.height);
}
