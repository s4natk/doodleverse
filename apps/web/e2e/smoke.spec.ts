import { expect, test } from "@playwright/test";

import { draw, shapes } from "./support";

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
