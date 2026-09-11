# Contributing

Start with README.md and docs/analysis-engine.md. Set up the Python environment and npm
workspace, migrate the local database, then run both applications. Keep changes focused:
an import-resolution improvement should include a small committed fixture and a test
showing the new evidence as well as ambiguity/negative cases.

Before a pull request, run Python lint/format, mypy, pytest, package build, frontend lint,
typecheck, component tests and frontend build. Run browser tests for UI changes. For
storage changes, add an Alembic migration and test upgrade/downgrade on a disposable DB.
Do not include credentials, copied production source, generated dependencies or fake metrics.

Use Conventional Commits, explain behavior and limitations, and keep documentation close
to the implementation. Apache-2.0 remains the project license; contributors retain their
copyright. Discuss substantial new analyzer contracts or public APIs before implementing.
There is no requirement to manufacture issues or PRs for trivial work.
