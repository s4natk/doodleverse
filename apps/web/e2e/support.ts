import type { Page, Route } from "@playwright/test";

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

/** Draw strokes on the sketch layer with the real mouse, in canvas pixels. */
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
      await page.mouse.move(box.x + x, box.y + y, { steps: 2 });
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
  line(x: number, y: number): Stroke[] {
    return [[[x, y], [x + 60, y + 20], [x + 120, y]]];
  },
};
