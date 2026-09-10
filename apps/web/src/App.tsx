import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpRight,
  Boxes,
  CheckCircle2,
  ChevronRight,
  Download,
  FileCode2,
  GitBranch,
  Github,
  Layers3,
  Moon,
  Network,
  Sun,
  Trash2,
} from "lucide-react";
import RepositoryForm from "./RepositoryForm";
import Explorer from "./Explorer";
import { api, type Run } from "./types";

export default function App() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState(
    () => localStorage.getItem("devlens-theme") ?? "dark",
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("devlens-theme", theme);
  }, [theme]);
  const refreshRuns = useCallback(async () => {
    const data = await api<Run[]>("/analysis");
    setRuns(data);
    return data;
  }, []);
  useEffect(() => {
    let active = true;
    void refreshRuns()
      .then((data) => {
        if (active && data[0]) setRun(data[0]);
      })
      .catch((e) => {
        if (active) setError(String(e.message));
      });
    return () => {
      active = false;
    };
  }, [refreshRuns]);
  const running = busy || run?.status === "queued" || run?.status === "running";

  useEffect(() => {
    if (!run || !["queued", "running"].includes(run.status)) return;
    let active = true;
    const timer = setInterval(() => {
      void api<Run>(`/analysis/${run.id}`)
        .then((next) => {
          if (!active) return;
          setRun(next);
          if (!["queued", "running"].includes(next.status))
            void refreshRuns().catch((e) => setError(e.message));
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    }, 1200);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [run, refreshRuns]);

  async function start(url: string) {
    setBusy(true);
    setError("");
    try {
      const next = await api<Run>("/analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: url }),
      });
      setRun(next);
      await refreshRuns();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!run) return;
    try {
      await api(`/analysis/${run.id}`, { method: "DELETE" });
      setRun(null);
      setConfirmDelete(false);
      await refreshRuns();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to repository explorer
      </a>
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="DevLens home">
          <span className="brand-mark">
            <Network size={21} />
          </span>
          <strong>DevLens</strong>
          <span className="version">MVP</span>
        </a>
        <div className="workspace-label">
          YOUR WORKSPACE <span>LOCAL</span>
        </div>
        <div className="nav-active">
          <Boxes size={17} /> Repository explorer
        </div>
        <div className="sidebar-section">
          <span>RECENT ANALYSES</span>
          <small>{runs.length}</small>
        </div>
        <div className="run-list">
          {runs.length === 0 ? (
            <p className="empty-recent">
              Your analyzed repositories will appear here.
            </p>
          ) : (
            runs.map((item) => (
              <button
                key={item.id}
                className={item.id === run?.id ? "run active" : "run"}
                onClick={() => {
                  setRun(item);
                  setError("");
                }}
              >
                <Github size={15} />
                <span>
                  {item.repository_url.split("/").slice(-2).join("/")}
                  <small>
                    {new Date(item.created_at).toLocaleDateString()} ·{" "}
                    {item.status}
                  </small>
                </span>
              </button>
            ))
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="local-note">
            <span className="status-dot" /> Local analysis workspace
          </div>
          <p>
            Evidence stays inspectable.
            <br />
            Your code is never executed.
          </p>
          <a
            href="https://github.com/dhaneshit008/devlens"
            target="_blank"
            rel="noreferrer"
          >
            <Github size={15} /> View project on GitHub{" "}
            <ArrowUpRight size={14} />
          </a>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="muted">Workspace</span>
            <ChevronRight size={14} />
            <span>Repository explorer</span>
          </div>
          <button
            className="icon-button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <p className="eyebrow">REPOSITORY INTELLIGENCE</p>
              <h1>
                Understand the impact
                <br className="mobile-break" /> before you change the code.
              </h1>
              <p className="subtitle">
                Map the architecture. Follow the evidence. Make your next change
                with context.
              </p>
            </div>
            <span className="deterministic">
              <CheckCircle2 size={14} /> Deterministic analysis
            </span>
          </div>
          <RepositoryForm onAnalyze={start} busy={Boolean(running)} />
          {error && (
            <div className="notice error" role="alert">
              <span>{error}</span>
              <button onClick={() => setError("")}>Dismiss</button>
            </div>
          )}
          {running && (
            <div className="notice" role="status">
              <span className="status-dot pulse" /> {run?.stage ?? "Submitting"}{" "}
              — fetching and analyzing a bounded repository snapshot. You can
              keep exploring the workspace.
            </div>
          )}
          {run?.status === "failed" && (
            <div className="notice error" role="alert">
              {run.error}
            </div>
          )}
          {run?.summary ? (
            <>
              <div className="repo-heading">
                <div>
                  <Github size={19} />
                  <h2>{run.repository_url.split("/").slice(-2).join("/")}</h2>
                  <span className="pill">Public</span>
                </div>
                <div className="repo-actions">
                  <a
                    href={`${run.repository_url}/commit/${run.summary.commit_sha}`}
                    target="_blank"
                    rel="noreferrer"
                    className="commit"
                  >
                    <GitBranch size={14} />
                    {run.summary.commit_sha.slice(0, 8)}
                  </a>
                  <a
                    className="icon-button"
                    href={`/api/v1/analysis/${run.id}/snapshot`}
                    download
                    aria-label="Export snapshot JSON"
                  >
                    <Download size={16} />
                  </a>
                  <button
                    className="icon-button"
                    aria-label="Delete analysis"
                    onClick={() => setConfirmDelete(true)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              {confirmDelete && (
                <div className="notice">
                  <span>Delete this stored analysis and graph?</span>
                  <button onClick={() => setConfirmDelete(false)}>
                    Cancel
                  </button>
                  <button className="danger" onClick={() => void remove()}>
                    Delete permanently
                  </button>
                </div>
              )}
              <div className="metrics">
                <div>
                  <span>
                    <FileCode2 size={16} />
                    Source files
                  </span>
                  <strong>{run.summary.source_file_count}</strong>
                  <small>Supported, analyzed files</small>
                </div>
                <div>
                  <span>
                    <Layers3 size={16} />
                    Languages
                  </span>
                  <strong>{Object.keys(run.summary.languages).length}</strong>
                  <small>
                    {Object.keys(run.summary.languages).join(" · ") ||
                      "No supported source detected"}
                  </small>
                </div>
                <div>
                  <span>
                    <Boxes size={16} />
                    Snapshot size
                  </span>
                  <strong>
                    {(run.summary.analyzed_bytes / 1024).toFixed(1)}
                    <em>KB</em>
                  </strong>
                  <small>UTF-8 source analyzed</small>
                </div>
                <div>
                  <span>
                    <CheckCircle2 size={16} />
                    Analysis method
                  </span>
                  <strong className="text-metric">AST + Git</strong>
                  <small>
                    Version {run.summary.analyzer_version} · commit pinned
                  </small>
                </div>
              </div>
              <Explorer key={run.id} run={run} setError={setError} />
            </>
          ) : (
            !running && (
              <section className="getting-started">
                <div className="intro-icon">
                  <Network size={32} />
                </div>
                <p className="eyebrow">A CLEARER VIEW OF YOUR CODEBASE</p>
                <h2>Your repository, connected.</h2>
                <p>
                  Start with a public repository. DevLens builds a real map of
                  its files,
                  <br /> declarations and imports, anchored to a specific
                  commit.
                </p>
                <div className="steps">
                  <div>
                    <span>01</span>
                    <h3>Map the source</h3>
                    <p>
                      Parse TypeScript, JavaScript and Python into an
                      inspectable graph.
                    </p>
                  </div>
                  <div>
                    <span>02</span>
                    <h3>Explore relationships</h3>
                    <p>
                      Follow imports and open the exact source lines behind each
                      connection.
                    </p>
                  </div>
                  <div>
                    <span>03</span>
                    <h3>Trace a change</h3>
                    <p>
                      Find direct consumers, transitive dependents and candidate
                      tests.
                    </p>
                  </div>
                </div>
              </section>
            )
          )}
          <footer className="page-footer">
            <span>DevLens · Repository digital twin</span>
            <span>Static evidence, with uncertainty made visible.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
