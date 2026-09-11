"""Explicit local-service configuration; never load repository configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./devlens.db"
    max_clone_seconds: int = 90
    max_repository_bytes: int = 200_000_000
    max_source_bytes: int = 20_000_000
    max_file_bytes: int = 500_000
    max_files: int = 2000
    max_tree_entries: int = 20000
    max_analysis_seconds: int = 180
    max_graph_nodes: int = 20000
    max_graph_edges: int = 50000


settings = Settings()
