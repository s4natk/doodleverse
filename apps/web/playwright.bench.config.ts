import { defineConfig } from "@playwright/test";

import base from "./playwright.config";

// The same E2E build and browser as the tests, one run at a time so nothing else competes for frames.
export default defineConfig({
  ...base,
  testDir: "bench",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  reporter: "list",
});
