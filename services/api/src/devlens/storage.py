"""Persisted analysis lifecycle and versioned snapshot documents."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from devlens.config import settings


class Base(DeclarativeBase):
    pass


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    repository_url: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    error: Mapped[str | None] = mapped_column(String(500))
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)


def make_engine(url: str) -> Any:
    return create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        pool_pre_ping=True,
    )


engine = make_engine(settings.database_url)
Session = sessionmaker(engine, expire_on_commit=False)
