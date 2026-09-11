# Deployment

Local development is the first supported mode. Docker Compose creates PostgreSQL,
one non-root API process and an unprivileged Nginx frontend. Host ports bind to loopback.
The API container has memory/CPU/PID limits and dropped capabilities. The database
network is internal and its port is not published. Dev database authentication uses
trust and is inappropriate for a shared/untrusted network.

`docker compose down` stops services and preserves the database volume. Deleting the
volume destroys analyses; do this only intentionally. Database migrations are Alembic
revisions; rollback is a development operation, not a substitute for backups.

Before public hosting: implement authentication/authorization, CSRF strategy, durable
job ownership and retries, hard repository-worker isolation, quotas, persistent job
timeouts, authenticated database access, TLS, retention policy and operational monitoring.
Do not just change a bind address and publish the current service.

CI builds and starts containers and waits for API/database and frontend connectivity.
Public cloud deployment, releases and release automation are not performed by this MVP.
