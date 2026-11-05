import { expect, test } from "@playwright/test";

import { draw, shapes } from "./support";

test("a first visit asks for a sun and only lets a drawing be recognized", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Start with a sun.")).toBeVisible();
  const recognize = page.getByRole("button", { name: "Recognize" });
  await expect(recognize).toBeDisabled();

  await draw(page, shapes.line(100, 200));
  await expect(recognize).toBeEnabled();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(recognize).toBeDisabled();
});
