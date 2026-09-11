"""Local, single-worker REST application with durable analysis records."""

import json
import logging
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text, update
from starlette.middleware.base import RequestResponseEndpoint

from devlens import __version__
from devlens.analysis import analyze
from devlens.config import settings
from devlens.impact import ImpactReport, impact
from devlens.ingestion import IngestionError, canonical_url, clone_public, read_sources
from devlens.models import Snapshot
from devlens.storage import AnalysisRun, Session, engine

logger = logging.getLogger("devlens")
logger.setLevel(logging.INFO)
admission = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with Session.begin() as session:
        session.execute(
            update(AnalysisRun)
            .where(AnalysisRun.status.in_(["queued", "running"]))
            .values(
                status="failed",
                stage="interrupted",
                error="Analysis interrupted by service restart. Submit again.",
            )
        )
    yield


app = FastAPI(title="DevLens", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def local_security(request: Request, call_next: RequestResponseEndpoint) -> Response:
    # Same-origin browser requests only. CLI clients without Origin remain supported.
    origin = request.headers.get("origin")
    expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
    if origin and origin != expected:
        return Response("Cross-origin requests are disabled.", status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


class AnalyzeRequest(BaseModel):
    repository_url: str = Field(max_length=300)

    @field_validator("repository_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return canonical_url(value)


def run_payload(row: AnalysisRun) -> dict[str, Any]:
    snapshot = row.snapshot
    return {
        "id": row.id,
        "repository_url": row.repository_url,
        "status": row.status,
        "stage": row.stage,
        "created_at": row.created_at.isoformat(),
        "error": row.error,
        "summary": {
            key: snapshot[key]
            for key in (
                "commit_sha",
                "analyzer_version",
                "languages",
                "source_file_count",
                "analyzed_bytes",
                "skipped",
            )
        }
        if snapshot
        else None,
    }


def get_run(run_id: str) -> AnalysisRun:
    with Session() as session:
        row = session.get(AnalysisRun, run_id)
        if row is None:
            raise HTTPException(404, "Analysis not found.")
        return row


def get_snapshot(run_id: str) -> Snapshot:
    row = get_run(run_id)
    if row.status != "completed" or row.snapshot is None:
        raise HTTPException(409, "Analysis is not complete.")
    return Snapshot.model_validate(row.snapshot)


def stage(run_id: str, value: str) -> None:
    with Session.begin() as session:
        session.execute(
            update(AnalysisRun)
            .where(AnalysisRun.id == run_id)
            .values(stage=value, status="running")
        )


def perform_analysis(run_id: str, repository_url: str) -> None:
    started = time.monotonic()
    sha: str | None = None
    current_stage = "fetching"
    success = False
    try:
        stage(run_id, current_stage)
        with clone_public(repository_url, settings) as repository:
            current_stage = "reading"
            stage(run_id, current_stage)
            source = read_sources(repository, settings)
            sha = source.commit_sha
            current_stage = "parsing"
            stage(run_id, current_stage)
            snapshot = analyze(source, repository_url, settings)
        current_stage = "persisting"
        with Session.begin() as session:
            session.execute(
                update(AnalysisRun)
                .where(AnalysisRun.id == run_id)
                .values(status="completed", stage="completed", snapshot=snapshot.model_dump())
            )
        success = True
    except Exception as exc:
        message = (
            str(exc)
            if isinstance(exc, IngestionError)
            else "Analysis failed internally. Check service operation and retry."
        )
        with Session.begin() as session:
            session.execute(
                update(AnalysisRun)
                .where(AnalysisRun.id == run_id)
                .values(status="failed", stage=current_stage, error=message)
            )
    finally:
        admission.release()
        logger.info(
            json.dumps(
                {
                    "analysis_id": run_id,
                    "repository": repository_url,
                    "commit_sha": sha,
                    "stage": current_stage,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "success": success,
                }
            )
        )


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "version": __version__}


@app.post("/api/v1/analysis", status_code=202)
def create_analysis(body: AnalyzeRequest, tasks: BackgroundTasks) -> dict[str, Any]:
    if not admission.acquire(blocking=False):
        raise HTTPException(
            429,
            "An analysis is already running. Retry when it finishes.",
            headers={"Retry-After": "5"},
        )
    try:
        with Session.begin() as session:
            row = AnalysisRun(
                id=str(uuid4()), repository_url=body.repository_url, status="queued", stage="queued"
            )
            session.add(row)
            session.flush()
            payload = run_payload(row)
        tasks.add_task(perform_analysis, row.id, row.repository_url)
        return payload
    except Exception:
        admission.release()
        raise


@app.get("/api/v1/analysis")
def list_analysis() -> list[dict[str, Any]]:
    with Session() as session:
        rows = session.scalars(
            select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(50)
        )
        return [run_payload(row) for row in rows]


@app.get("/api/v1/analysis/{run_id}")
def read_analysis(run_id: str) -> dict[str, Any]:
    return run_payload(get_run(run_id))


@app.delete("/api/v1/analysis/{run_id}", status_code=204)
def delete_analysis(run_id: str) -> Response:
    row = get_run(run_id)
    if row.status in {"queued", "running"}:
        raise HTTPException(409, "Wait for this analysis to finish before deleting it.")
    with Session.begin() as session:
        session.delete(session.merge(row))
    return Response(status_code=204)


@app.get("/api/v1/analysis/{run_id}/snapshot", response_model=Snapshot)
def export_snapshot(run_id: str) -> Snapshot:
    return get_snapshot(run_id)


@app.get("/api/v1/analysis/{run_id}/graph")
def graph(
    run_id: str,
    q: str = "",
    kind: str = "",
    language: str = "",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 150,
) -> dict[str, Any]:
    snapshot = get_snapshot(run_id)
    matches = [
        node
        for node in snapshot.nodes
        if (not kind or node.kind == kind)
        and (not language or node.language == language)
        and q.lower() in (node.path + " " + node.label).lower()
    ]
    visible = matches[offset : offset + limit]
    ids = {node.id for node in visible}
    return {
        "nodes": visible,
        "edges": [edge for edge in snapshot.edges if edge.source in ids and edge.target in ids],
        "total": len(matches),
        "offset": offset,
        "limit": limit,
        "truncated": offset + limit < len(matches),
        "commit_sha": snapshot.commit_sha,
        "limitations": snapshot.limitations,
    }


@app.get("/api/v1/analysis/{run_id}/impact", response_model=ImpactReport)
def change_impact(run_id: str, target: str) -> ImpactReport:
    try:
        return impact(get_snapshot(run_id), target)
    except KeyError as exc:
        raise HTTPException(404, "Target node not found.") from exc
