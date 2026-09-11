# Local development

The [README](../README.md) is the canonical setup and check sequence. Run all commands
from the repository root unless specified. `.env` is optional; `.env.example` contains
only the local database URL. The deterministic MVP needs no GitHub or AI credentials.

Use Python 3.12 and Node 24 to match CI. `requirements.lock` constrains the full tested
Python environment; `package-lock.json` locks npm workspaces. Refresh constraints only
after tests and both builds pass. Run `alembic upgrade head` before starting the API.
Never call SQLAlchemy `create_all` in production; it is only used for isolated test DBs.

Tests create committed temporary Git repositories and do not run their programs. If a
Windows sandbox denies temporary directory access, run tests in a normal development
shell or supply a writable pytest `--basetemp` directory. On some portable Git builds,
the HTTPS helper resides in `mingw64/bin`; ingestion detects that layout.

The Vite dev server and API bind to loopback. Keep `localhost` or `127.0.0.1` consistent
in the browser URL; API calls are same-origin through Vite's proxy. One API worker is
required for admission control and restart recovery. Migrations are run explicitly by
developers and automatically by the API container entrypoint.
