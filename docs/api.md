# REST API v1

Interactive OpenAPI: `http://localhost:8000/docs` when the local API is running.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/health` | Database connectivity and application version |
| POST | `/api/v1/analysis` | `{ "repository_url": "https://github.com/owner/repo" }`; 202 with run ID |
| GET | `/api/v1/analysis` | Most recent 50 analysis runs |
| GET | `/api/v1/analysis/{id}` | Status, stage, safe error and snapshot summary |
| GET | `/api/v1/analysis/{id}/graph` | `q`, `kind`, `language`, `offset`, `limit` (1–500) |
| GET | `/api/v1/analysis/{id}/impact?target={node_id}` | Direct/transitive consumers with evidence paths |
| GET | `/api/v1/analysis/{id}/snapshot` | Complete bounded schema-v1 JSON export |
| DELETE | `/api/v1/analysis/{id}` | Delete finished/failed analysis; 204 |

States: queued → running → completed or failed. Stages: fetching, reading, parsing,
completed; failures record their stage. Poll at roughly one-second intervals. There is
one active job per process; excess POSTs receive 429 + Retry-After. Do not run multiple
API workers. Restarted in-flight jobs become failed and require resubmission.

Missing run/target: 404. Invalid URL/query: 422. Incomplete graph or deletion of a running
job: 409. Browser cross-origin requests: 403. This local API is unauthenticated and must
not be exposed publicly. Error responses never include Git stderr or source content.
