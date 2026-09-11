import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import ImpactPanel from "./ImpactPanel";
import type { ImpactReport, Run } from "./types";

it("shows provenance and a source link for transitive impact", async () => {
  const evidence = {
    path: "consumer.ts",
    start_line: 3,
    end_line: 3,
    method: "AST import",
  };
  const node = {
    id: "file:consumer.ts",
    kind: "file",
    path: "consumer.ts",
    label: "consumer.ts",
    language: "TypeScript",
    evidence,
    is_test: false,
  };
  const report: ImpactReport = {
    target: node,
    scope: "file",
    direct: [],
    indirect: [
      {
        node,
        distance: 2,
        classification: "inferred reachability",
        evidence_path: [
          {
            id: "e1",
            source: node.id,
            target: "file:target.ts",
            kind: "imports",
            evidence,
          },
        ],
      },
    ],
    candidate_tests: [],
    limitations: ["Static reachability is not a prediction of breakage."],
  };
  const run: Run = {
    id: "fixture",
    repository_url: "https://github.com/fixture/repo",
    status: "completed",
    stage: "completed",
    created_at: "",
    error: null,
    summary: {
      commit_sha: "a".repeat(40),
      analyzer_version: "0.4.0",
      languages: {},
      source_file_count: 2,
      analyzed_bytes: 20,
      skipped: {},
    },
  };
  render(<ImpactPanel report={report} run={run} />);
  await userEvent.click(screen.getByText("consumer.ts", { exact: true }));
  expect(screen.getByText("inferred reachability")).toBeVisible();
  expect(screen.getByRole("link", { name: "Line 3" })).toHaveAttribute(
    "href",
    `https://github.com/fixture/repo/blob/${"a".repeat(40)}/consumer.ts#L3-L3`,
  );
  expect(screen.getByText(report.limitations[0])).toBeVisible();
});
