import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App";
vi.mock("./Explorer", () => ({ default: () => null }));
vi.mock("./Architecture", () => ({ default: () => null }));
afterEach(() => vi.restoreAllMocks());

it("binds deletion confirmation to one run and allows failed-run cleanup", async () => {
  const summary = {
    commit_sha: "a".repeat(40),
    analyzer_version: "0.5.0",
    languages: { TypeScript: 1 },
    source_file_count: 1,
    analyzed_bytes: 10,
    skipped: {},
  };
  const runs = ["alpha", "beta", "failed"].map((id) => ({
    id,
    repository_url: `https://github.com/audit/${id}`,
    status: id === "failed" ? "failed" : "completed",
    stage: "completed",
    created_at: "2026-09-11T00:00:00Z",
    error: id === "failed" ? "Fixture failure" : null,
    summary: id === "failed" ? null : summary,
  }));
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (_input, init) =>
      init?.method === "DELETE"
        ? new Response(null, { status: 204 })
        : new Response(JSON.stringify(runs), { status: 200 }),
    );
  render(<App />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Delete analysis" }),
  );
  await userEvent.click(screen.getByRole("button", { name: /audit\/beta/ }));
  expect(
    screen.queryByRole("button", { name: "Delete permanently" }),
  ).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: /audit\/failed/ }));
  await userEvent.click(
    screen.getByRole("button", { name: "Delete failed analysis" }),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Delete permanently" }),
  );
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith("/api/v1/analysis/failed", {
      method: "DELETE",
    }),
  );
});
