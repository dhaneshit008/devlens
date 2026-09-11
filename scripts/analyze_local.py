"""Analyze committed local Git source using the same product engine."""

import argparse
from pathlib import Path

from devlens.analysis import analyze
from devlens.config import Settings
from devlens.impact import impact
from devlens.ingestion import IngestionError, read_sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--impact", help="Repository-relative file path")
    args = parser.parse_args()
    try:
        snapshot = analyze(read_sources(args.repository.resolve(), Settings()), "local repository")
        result = impact(snapshot, "file:" + args.impact) if args.impact else snapshot
    except (IngestionError, KeyError) as exc:
        parser.exit(1, f"Analysis failed: {exc}\n")
    payload = result.model_dump_json(indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
