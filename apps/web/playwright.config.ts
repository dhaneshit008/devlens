import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

const python =
  process.platform === "win32"
    ? resolve("../../.venv/Scripts/python.exe")
    : "python";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `"${python}" ../../tests/e2e_server.py`,
      url: "http://127.0.0.1:8000/api/v1/health",
      timeout: 60_000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      timeout: 60_000,
      reuseExistingServer: false,
    },
  ],
});
