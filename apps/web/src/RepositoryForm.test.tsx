import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import RepositoryForm from "./RepositoryForm";

describe("repository ingestion form", () => {
  it("submits a public URL through the actual form", async () => {
    const onAnalyze = vi.fn().mockResolvedValue(undefined);
    render(<RepositoryForm onAnalyze={onAnalyze} busy={false} />);
    await userEvent.type(
      screen.getByLabelText("Public GitHub repository"),
      "https://github.com/owner/repo",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Analyze repository" }),
    );
    expect(onAnalyze).toHaveBeenCalledWith("https://github.com/owner/repo");
  });
  it("rejects non-GitHub URLs without starting a job", async () => {
    const onAnalyze = vi.fn();
    render(<RepositoryForm onAnalyze={onAnalyze} busy={false} />);
    await userEvent.type(
      screen.getByLabelText("Public GitHub repository"),
      "https://evil.example/repo",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Analyze repository" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "public GitHub repository URL",
    );
    expect(onAnalyze).not.toHaveBeenCalled();
  });
  it("prevents duplicate submissions while analysis runs", () => {
    render(<RepositoryForm onAnalyze={vi.fn()} busy={true} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
