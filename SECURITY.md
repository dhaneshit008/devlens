# Security

DevLens currently supports local, single-user public-repository analysis. It is not ready
for unauthenticated public hosting or private repositories. Keep ports bound to loopback.
The development PostgreSQL service uses trust authentication only on an internal Docker
network. Configure secret-managed database authentication before shared deployment.

Repository input is untrusted. URL allowlisting, isolated Git configuration, disabled
credentials/hooks, no checkout, no source execution, symlink/submodule rejection and
resource limits are part of the boundary. Container limits strengthen it. Git itself
and native parser libraries remain trusted dependencies; keep them patched. Periodic
download checks and between-file parser deadlines are not hard OS resource guarantees.

Do not send secrets in issue reports. Use GitHub private vulnerability reporting if it
is enabled for this repository; otherwise contact the maintainer through their profile
to establish a private channel before sharing sensitive details. Do not publish working
exploits before a fix can be coordinated. No response SLA is promised by this early project.

See docs/privacy-architecture.md for stored data and deletion behavior. CodeQL, dependency
review and Dependabot are configured; their presence is not a claim that all code is secure.

Architecture JSON and tsconfig JSONC are read from bounded regular Git blobs and parsed
only as data. Invalid architecture rules fail explicitly; unsupported tsconfig inheritance
is reported as a limitation. Host headers are allowlisted (`localhost`, `127.0.0.1`) in
addition to same-origin checks, including when an attacker supplies matching Host/Origin.
This does not provide user authentication. Configure `ALLOWED_HOSTS` as a JSON array only
for trusted deployment hostnames; keep loopback binding for local use.

Schema-v2 source excerpts may contain sensitive material already present in a public
repository. Keep the analysis database and exports under the same access restrictions as
source data; deleting a run does not remove backups or previously downloaded exports.
