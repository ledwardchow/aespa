import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import path from "node:path";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  workers: process.env.CI ? 2 : 3,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  outputDir: path.join(tmpdir(), "aespa-ui-test-results"),
  use: {
    baseURL: process.env.AESPA_UI_TEST_URL || "http://127.0.0.1:5179",
    viewport: { width: 1440, height: 1000 },
    serviceWorkers: "block",
    launchOptions: process.env.AESPA_CHROME_PATH
      ? { executablePath: process.env.AESPA_CHROME_PATH }
      : {},
    screenshot: "only-on-failure",
  },
  webServer: process.env.AESPA_UI_TEST_URL
    ? undefined
    : {
        command: process.env.AESPA_UI_TEST_BUILD
          ? "npm run preview -- --host 127.0.0.1 --port 5179 --strictPort"
          : "npm run dev -- --host 127.0.0.1 --port 5179 --strictPort",
        url: "http://127.0.0.1:5179",
        reuseExistingServer: !process.env.CI,
      },
});
