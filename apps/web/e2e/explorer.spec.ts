import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("public URL → committed analysis → graph → impact evidence → deletion", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  if (process.env.DEVLENS_CAPTURE) {
    mkdirSync("../../docs/assets", { recursive: true });
    await page.screenshot({
      path: "../../docs/assets/empty-workspace.png",
      fullPage: true,
    });
  }
  await page
    .getByLabel("Public GitHub repository")
    .fill("https://github.com/devlens-fixtures/mini-repo");
  await page
    .getByRole("button", { name: "Analyze repository", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "devlens-fixtures/mini-repo" }),
  ).toBeVisible();
  await expect(page.getByLabel("Interactive repository graph")).toBeVisible();
  await page.getByLabel("Search graph").fill("math");
  await expect(
    page.getByText("1–1 of 1 nodes", { exact: false }),
  ).toBeVisible();
  await page
    .locator(".react-flow__node")
    .filter({ hasText: "math.ts" })
    .click();
  await expect(
    page.getByRole("button", { name: "Simulate change impact" }),
  ).toBeVisible();
  await page.getByLabel("List view", { exact: true }).click();
  await page.getByRole("button", { name: "src/math.ts", exact: true }).click();
  const details = page.getByRole("complementary", { name: "Node details" });
  await expect(
    details.getByRole("link", { name: "Inspect source evidence" }),
  ).toHaveAttribute("href", /\/blob\/[a-f0-9]{40}\/src\/math.ts#L1-L1/);
  await page.getByRole("button", { name: "Simulate change impact" }).click();
  await expect(
    page.getByRole("region", { name: "Impact results" }),
  ).toBeVisible();
  await page.getByText("tests/service.test.ts", { exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Line 1", exact: false }).first(),
  ).toBeVisible();
  await expect(
    page
      .locator(".impact-entry[open]")
      .getByText("inferred reachability", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Search graph").fill("");
  await page.getByLabel("Graph view", { exact: true }).click();
  await expect(
    page.getByText("1–8 of 8 nodes", { exact: false }),
  ).toBeVisible();
  if (process.env.DEVLENS_CAPTURE) {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: "../../docs/assets/fixture-analysis.png",
      fullPage: true,
    });
  }
  await page.getByLabel("Switch to light mode").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  if (process.env.DEVLENS_CAPTURE) {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: "../../docs/assets/fixture-analysis-light.png",
      fullPage: true,
    });
  }
  await page.getByLabel("Search graph").fill("no-such-source-file");
  await expect(page.getByText("No nodes match these filters.")).toBeVisible();
  await page.getByLabel("Delete analysis", { exact: true }).click();
  await page.getByRole("button", { name: "Delete permanently" }).click();
  await expect(
    page.getByRole("heading", { name: "Your repository, connected." }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("small viewport remains usable without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByLabel("Public GitHub repository")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Analyze repository", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
