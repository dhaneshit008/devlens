import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import Architecture from "./Architecture";
import type { ArchitectureSummary, Relationship } from "./architecture-types";
import type { Run } from "./types";

vi.mock("./ArchitectureMap", () => ({
  default: () => <div>Layer visualization</div>,
  CycleMap: () => <div>Cycle visualization</div>,
}));
afterEach(() => vi.restoreAllMocks());
const run: Run = {
  id: "a",
  repository_url: "https://github.com/fixture/architecture",
  status: "completed",
  stage: "completed",
  created_at: "",
  error: null,
  summary: {
    commit_sha: "a".repeat(40),
    analyzer_version: "0.5.0",
    languages: { TypeScript: 2 },
    source_file_count: 2,
    analyzed_bytes: 30,
    skipped: {},
  },
};
const summary: ArchitectureSummary = {
  commit_sha: "a".repeat(40),
  configuration: ".devlens.json",
  direction: "consumer → dependency",
  layers: { domain: 1, frontend: 1 },
  relationships: [{ source: "domain", target: "frontend", count: 1 }],
  rules: [{ id: "boundary", from: "domain", allow: null, deny: ["frontend"] }],
  metrics: { violations: 1 },
};
const evidence = {
  path: "domain/a.ts",
  start_line: 1,
  end_line: 1,
  method: "ES import",
  snippet: [{ number: 1, text: "import '../frontend/a';" }],
};
const relation: Relationship = {
  edge: { id: "e", source: "a", target: "b", kind: "imports", evidence },
  source: {
    id: "a",
    kind: "file",
    label: "domain/a.ts",
    path: "domain/a.ts",
    language: "TypeScript",
    is_test: false,
    evidence,
  },
  target: {
    id: "b",
    kind: "file",
    label: "frontend/a.ts",
    path: "frontend/a.ts",
    language: "TypeScript",
    is_test: false,
    evidence: {
      ...evidence,
      path: "frontend/a.ts",
      snippet: [{ number: 1, text: "export const value = 1;" }],
    },
  },
  source_layer: "domain",
  target_layer: "frontend",
  rule_ids: ["boundary"],
  status: "Violation",
};
function mockApi(items: unknown[] = [relation], overview = summary) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const body = url.endsWith("/architecture")
      ? overview
      : {
          items,
          total: items.length,
          offset: 0,
          limit: 20,
          truncated: false,
          commit_sha: "a".repeat(40),
        };
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

it("drills from actual layer counts to side-by-side import evidence", async () => {
  mockApi();
  render(<Architecture run={run} />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Inspect domain → frontend" }),
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Inspect line 1" }),
  );
  expect(screen.getByText("import '../frontend/a';")).toBeVisible();
  expect(screen.getByText("export const value = 1;")).toBeVisible();
  expect(screen.getAllByRole("link")[0]).toHaveAttribute(
    "href",
    `https://github.com/fixture/architecture/blob/${"a".repeat(40)}/domain/a.ts#L1-L1`,
  );
});

it("uses source layer, rule, language and path filters for violations", async () => {
  const fetch = mockApi();
  render(<Architecture run={run} />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Violations" }),
  );
  await userEvent.selectOptions(
    screen.getByLabelText("Source layer"),
    "domain",
  );
  await userEvent.selectOptions(screen.getByLabelText("Rule"), "boundary");
  await userEvent.selectOptions(
    screen.getByLabelText("Language"),
    "TypeScript",
  );
  await userEvent.type(screen.getByLabelText("Path"), "domain");
  await waitFor(() =>
    expect(
      fetch.mock.calls.some(
        ([url]) =>
          String(url).includes("source_layer=domain") &&
          String(url).includes("rule=boundary") &&
          String(url).includes("language=TypeScript") &&
          String(url).includes("path=domain"),
      ),
    ).toBe(true),
  );
});

it("does not present missing rules as a compliance verdict", async () => {
  mockApi([], {
    ...summary,
    rules: [],
    relationships: [],
    configuration: null,
  });
  render(<Architecture run={run} />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Violations" }),
  );
  expect(
    await screen.findByText(
      /absence of violations is not a compliance verdict/,
    ),
  ).toBeVisible();
});

it("explains legacy snapshot errors", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        detail:
          "This legacy snapshot has no architecture data. Analyze the repository again.",
      }),
      { status: 409 },
    ),
  );
  render(<Architecture run={run} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Analyze the repository again.",
  );
});

it("presents cycle selection and exact edge evidence", async () => {
  const cycle = {
    id: "file-cycle-1",
    kind: "file",
    members: ["a", "b"],
    path: ["a", "b", "a"],
    edge_ids: ["e"],
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(
    async (input) =>
      new Response(
        JSON.stringify(
          String(input).endsWith("/architecture")
            ? summary
            : String(input).includes("/cycles/file-cycle-1")
              ? { commit_sha: "a".repeat(40), cycle, relationships: [relation] }
              : {
                  items: [cycle],
                  total: 1,
                  offset: 0,
                  limit: 20,
                  truncated: false,
                  commit_sha: "a".repeat(40),
                },
        ),
        { status: 200 },
      ),
  );
  render(<Architecture run={run} />);
  await userEvent.click(await screen.findByRole("button", { name: "Cycles" }));
  await userEvent.click(
    await screen.findByRole("button", { name: "file-cycle-1 · 2 members" }),
  );
  await userEvent.click(
    await screen.findByRole("button", {
      name: "domain/a.ts → frontend/a.ts · line 1",
    }),
  );
  expect(screen.getByText("import '../frontend/a';")).toBeVisible();
});
