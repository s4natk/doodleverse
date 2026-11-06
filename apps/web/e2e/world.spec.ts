import { expect, test } from "@playwright/test";

import { answer, confirm, serve, shapes, tapWorld, worldStats } from "./support";

test("tapping a settled cloud starts rain, and reset puts the walkthrough back", async ({ page }) => {
  await serve(page, (_body, index) => ({ body: answer(["sun", "cloud"][index] ?? "tree") }));

  await page.goto("/");
  await confirm(page, "sun", shapes.sun(220, 120));
  await confirm(page, "cloud", shapes.cloud(380, 100));
  await expect(page.getByText("2 things in the world")).toBeVisible();

  await expect.poll(async () => (await worldStats(page)).clouds[0]?.settled === true).toBe(true);
  const cloud = (await worldStats(page)).clouds[0];
  await tapWorld(page, [cloud.x, cloud.y]);
  await expect.poll(async () => (await worldStats(page)).raining).toBe(1);

  await page.getByRole("button", { name: "Reset" }).click();
  await expect(page.getByText("0 things in the world")).toBeVisible();
  await expect(page.getByText("Start with a sun.")).toBeVisible();
  await expect.poll(async () => (await worldStats(page)).entities).toBe(0);
});

test("clear and reset return bodies, views, and listeners to the empty world's counts", async ({ page }) => {
  await serve(page, (_body, index) => ({
    body: answer(["sun", "cloud", "car", "sun"][index] ?? "sun"),
  }));

  await page.goto("/");
  const idle = await worldStats(page);
  expect(idle).toMatchObject({
    entities: 0,
    views: 0,
    bodies: 3,
    physicsListeners: 1,
    motionListeners: 1,
    raining: 0,
  });
  expect(idle.tickerListeners).toBeGreaterThan(0);
  expect(idle.displayObjects).toBeGreaterThan(0);

  await confirm(page, "sun", shapes.sun(180, 110));
  await confirm(page, "cloud", shapes.cloud(360, 90));
  await confirm(page, "car", shapes.car(80, 420));
  await expect(page.getByText("3 things in the world")).toBeVisible();

  await expect.poll(async () => (await worldStats(page)).entities).toBe(3);
  await expect.poll(async () => (await worldStats(page)).views).toBe(3);
  await expect.poll(async () => (await worldStats(page)).bodies).toBe(4);

  const busy = await worldStats(page);
  expect(busy.displayObjects).toBeGreaterThan(idle.displayObjects);
  expect(busy.tickerListeners).toBe(idle.tickerListeners);
  expect(busy.physicsListeners).toBe(idle.physicsListeners);
  expect(busy.motionListeners).toBe(idle.motionListeners);

  await page.getByRole("button", { name: "Clear world" }).click();
  await expect(page.getByText("0 things in the world")).toBeVisible();
  await expect.poll(async () => (await worldStats(page)).entities).toBe(0);
  expect(await worldStats(page)).toMatchObject({
    entities: 0,
    views: 0,
    displayObjects: idle.displayObjects,
    bodies: idle.bodies,
    tickerListeners: idle.tickerListeners,
    physicsListeners: idle.physicsListeners,
    motionListeners: idle.motionListeners,
    raining: 0,
  });

  await confirm(page, "sun", shapes.sun(200, 100));
  await expect(page.getByText("1 thing in the world")).toBeVisible();
  await page.getByRole("button", { name: "Reset" }).click();
  await expect(page.getByText("0 things in the world")).toBeVisible();
  expect(await worldStats(page)).toMatchObject({
    entities: 0,
    views: 0,
    displayObjects: idle.displayObjects,
    bodies: idle.bodies,
    tickerListeners: idle.tickerListeners,
    physicsListeners: idle.physicsListeners,
    motionListeners: idle.motionListeners,
  });

  await page.evaluate(() => (window as unknown as { __doodleverseWorld: { destroy(): void } }).__doodleverseWorld.destroy());
  expect(await worldStats(page)).toMatchObject({
    entities: 0,
    views: 0,
    displayObjects: 0,
    bodies: 0,
    tickerListeners: 0,
    physicsListeners: 0,
    motionListeners: 0,
    raining: 0,
  });
});
