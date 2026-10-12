import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  workers: 1,
  testDir: "./e2e",
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    ...(process.env.TEST_FIREFOX === "1"
      ? [{ name: "firefox", use: { ...devices["Desktop Firefox"] } }]
      : []),
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
});
