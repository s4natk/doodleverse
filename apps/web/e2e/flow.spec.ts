import { expect, test } from "@playwright/test";

import { answer, confirm, draw, serve, shapes } from "./support";

test("a mocked /predict names a drawing, and confirming it puts it in the world", async ({ page }) => {
  const received = await serve(page, (_body, index) => ({
    body: answer(["sun", "cloud"][index] ?? "tree"),
  }));

  await page.goto("/");
  await expect(page.getByText("Start with a sun.")).toBeVisible();
  await expect(page.getByText("0 things in the world")).toBeVisible();

  await confirm(page, "sun", shapes.sun(220, 120));
  await expect(page.getByText("1 thing in the world")).toBeVisible();
  await expect(page.getByText("Now a cloud for the sky.")).toBeVisible();

  await confirm(page, "cloud", shapes.cloud(380, 100));
  await expect(page.getByText("2 things in the world")).toBeVisible();
  await expect(page.getByText("Tap the cloud for rain, or draw a tree, a flower, a car, or a cat.")).toBeVisible();

  expect(received).toHaveLength(2);
  for (const body of received) {
    const request = body as { canvas: { width: number; height: number }; strokes: unknown[] };
    expect(request.canvas.width).toBeGreaterThan(100);
    expect(request.canvas.height).toBeGreaterThan(100);
    expect(request.strokes.length).toBeGreaterThan(0);
  }
});

test("a down recognizer shows the error and lets the person retry", async ({ page }) => {
  await serve(page, (_body, index) => (index === 0 ? "offline" : { body: answer("sun") }));

  await page.goto("/");
  await draw(page, shapes.sun(220, 120));
  await page.getByRole("button", { name: "Recognize" }).click();
  await expect(page.getByText("That didn't work.")).toBeVisible();
  await expect(page.getByText("Could not reach the recognizer. Check that the API is running.")).toBeVisible();

  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("button", { name: "Yes, it's a sun" })).toBeVisible();
  await page.getByRole("button", { name: "Yes, it's a sun" }).click();
  await expect(page.getByText("1 thing in the world")).toBeVisible();
});
