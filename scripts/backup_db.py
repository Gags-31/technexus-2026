"""Create a consistent SQLite backup using the online backup API."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="backend/technexus.db", help="Source SQLite database")
    parser.add_argument("--output", required=True, help="Backup destination")
    args = parser.parse_args()
    backup(Path(args.db), Path(args.output))
    print(f"Backup written to {args.output}")


if __name__ == "__main__":
    main()
