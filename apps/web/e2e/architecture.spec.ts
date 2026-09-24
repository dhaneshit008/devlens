import { expect, test } from "@playwright/test";

test("architecture rules, cycle evidence and impact context", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Public GitHub repository")
    .fill("https://github.com/devlens-fixtures/architecture");
  await page
    .getByRole("button", { name: "Analyze repository", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "devlens-fixtures/architecture" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Architecture intelligence" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Inspect frontend → api" }),
  ).toBeVisible();
  if (process.env.DEVLENS_ARCHITECTURE_CAPTURE)
    await page.screenshot({
      path: "../../docs/assets/architecture-map.png",
      fullPage: true,
    });
  await page.getByRole("button", { name: "Violations", exact: true }).click();
  await expect(
    page.getByRole("cell", { name: "domain-boundary", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Inspect line 1", exact: true })
    .click();
  const evidence = page.getByRole("region", { name: "Relationship evidence" });
  await expect(
    evidence.getByText("import '../frontend/shared';", { exact: true }),
  ).toBeVisible();
  await expect(evidence.getByRole("link").first()).toHaveAttribute(
    "href",
    /\/blob\/[a-f0-9]{40}\/domain\/service.ts#L1-L1/,
  );
  if (process.env.DEVLENS_ARCHITECTURE_CAPTURE)
    await page.screenshot({
      path: "../../docs/assets/architecture-evidence.png",
      fullPage: true,
    });
  await page.getByLabel("Language", { exact: true }).selectOption("TypeScript");
  await page.getByLabel("Path", { exact: true }).fill("no-such-file");
  await expect(page.getByText(/No violations match/)).toBeVisible();
  await page.getByRole("button", { name: "Cycles", exact: true }).click();
  await page.getByLabel("Cycle type").selectOption("file");
  await page
    .getByRole("button", { name: "file-cycle-1 · 3 members", exact: true })
    .click();
  await expect(page.getByLabel("Cycle graph")).toBeVisible();
  await page
    .getByRole("button", {
      name: "domain/a.ts → domain/b.ts · line 1",
      exact: true,
    })
    .click();
  await expect(
    evidence.getByText("import './b';", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Repository explorer", exact: true })
    .click();
  await page.getByLabel("Search graph").fill("path:repository/store");
  await expect(page.locator(".react-flow__node")).toHaveCount(1);
  await page.locator(".react-flow__node").focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Simulate change impact" }).click();
  await expect(
    page.getByText("Affected layers:", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Related violations:", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Delete analysis", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Delete permanently", exact: true })
    .click();
});

test("mobile architecture remains usable with history selection", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByLabel("Recent analyses", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Public GitHub repository")
    .fill("https://github.com/devlens-fixtures/architecture");
  await page
    .getByRole("button", { name: "Analyze repository", exact: true })
    .click();
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await page
    .getByRole("button", { name: "Layer evidence", exact: true })
    .click();
  await expect(page.getByRole("table")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Delete analysis", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Delete permanently", exact: true })
    .click();
});
