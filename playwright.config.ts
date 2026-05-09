import { defineConfig } from "@playwright/test";

const baseURL =
  process.env.CARTFLOW_BASE_URL?.replace(/\/+$/, "") || "http://127.0.0.1:8000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  timeout: 120_000,
  use: {
    baseURL,
    trace: "on-first-retry",
    ignoreHTTPSErrors: true,
  },
});
