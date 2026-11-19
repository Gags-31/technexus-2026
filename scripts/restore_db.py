"""Restore a SQLite database from a backup. Stop the app before restoring."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def restore(source: Path, destination: Path) -> None:
    if not source.exists():
        raise SystemExit(f"Backup not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(destination) + suffix)
        if sidecar.exists():
            sidecar.unlink()
    shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="backend/technexus.db", help="Destination SQLite database")
    parser.add_argument("--input", required=True, help="Backup file to restore")
    args = parser.parse_args()
    restore(Path(args.input), Path(args.db))
    print(f"Database restored from {args.input}")


if __name__ == "__main__":
    main()
