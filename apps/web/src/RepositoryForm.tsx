import { useState, type FormEvent } from "react";
import { ArrowRight, Github, LoaderCircle } from "lucide-react";

export default function RepositoryForm({
  onAnalyze,
  busy,
}: {
  onAnalyze: (url: string) => Promise<void>;
  busy: boolean;
}) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = url.trim();
    if (
      !/^https:\/\/github\.com\/[A-Za-z0-9][A-Za-z0-9-]*\/[A-Za-z0-9_.-]+\/?$/.test(
        value,
      )
    ) {
      setError(
        "Enter a public GitHub repository URL, such as https://github.com/owner/repo.",
      );
      return;
    }
    setError("");
    await onAnalyze(value);
  }
  return (
    <form onSubmit={submit} className="repository-form">
      <label htmlFor="repository-url">Public GitHub repository</label>
      <div className="input-row">
        <Github size={18} aria-hidden="true" />
        <input
          id="repository-url"
          type="url"
          placeholder="https://github.com/owner/repository"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          required
          disabled={busy}
          aria-describedby={error ? "url-error" : "url-help"}
        />
        <button className="primary" disabled={busy}>
          {busy ? (
            <LoaderCircle size={16} className="spin" />
          ) : (
            <ArrowRight size={16} />
          )}{" "}
          {busy ? "Analyzing…" : "Analyze repository"}
        </button>
      </div>
      {error ? (
        <p id="url-error" role="alert" className="error-text">
          {error}
        </p>
      ) : (
        <p id="url-help">
          Static analysis only · Source code is never executed · No AI key
          required
        </p>
      )}
    </form>
  );
}
