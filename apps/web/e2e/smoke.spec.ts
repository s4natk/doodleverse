import { expect, test } from "@playwright/test";

import { answer, confirm, draw, serve, shapes, worldStats } from "./support";

test("a first visit asks for a sun and only lets a drawing be recognized", async ({ page }) => {
  await page.goto("/draw");
  await expect(page.getByText("Start with a sun.")).toBeVisible();
  const recognize = page.getByRole("button", { name: "Recognize" });
  await expect(recognize).toBeDisabled();

  await draw(page, shapes.line(100, 200));
  await expect(recognize).toBeEnabled();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(recognize).toBeDisabled();
});

test("the cover turns the page to the sketchbook, and the sketchbook turns back", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Bring it to life.");
  await page.getByRole("link", { name: "Start drawing" }).first().click();
  await expect(page).toHaveURL(/\/draw$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Your sketchbook");
  await expect(page.getByLabel("Drawing area")).toBeVisible();

  await page.getByRole("link", { name: "Cover" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Draw it.");
});

test.describe("with reduced motion asked for", () => {
  test.use({ reducedMotion: "reduce" });

  test("the cover still draws in, the page still turns, and a cloud still drifts", async ({ page }) => {
    await serve(page, () => ({ body: answer("cloud") }));
    await page.goto("/");
    // A finished draw-in holds its last frame, so it is still listed after the sketch is done.
    const drawIns = await page.locator("svg .draw").first().evaluate((node) => node.getAnimations().length);
    expect(drawIns).toBeGreaterThan(0);

    await page.getByRole("link", { name: "Start drawing" }).first().click();
    await expect(page.locator('#sheet[data-turn="forward"]')).toBeAttached();
    await expect(page).toHaveURL(/\/draw$/);

    await confirm(page, "cloud", shapes.cloud(380, 100));
    await expect.poll(async () => (await worldStats(page)).clouds[0]?.settled === true).toBe(true);
    const start = (await worldStats(page)).clouds[0].x;
    await expect.poll(async () => Math.abs((await worldStats(page)).clouds[0].x - start)).toBeGreaterThan(5);
  });
});
