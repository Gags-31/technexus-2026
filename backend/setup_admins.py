"""One-time administrator setup.

Usage:  python -m setup_admins
Optionally set ADMIN1_TEMP_PASSWORD / ADMIN2_TEMP_PASSWORD in backend/.env.
Credentials are written only to the git-ignored .admin_credentials.txt file.
"""
from __future__ import annotations

import getpass
import os
import secrets
import string
from pathlib import Path

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Administrator
from app.security import hash_password


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "Tnx!" + "".join(secrets.choice(alphabet) for _ in range(16))


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Administrator).count()
        if existing >= 2:
            print("Both administrator accounts already exist. Setup skipped.")
            return
        specs = [
            ("organiser", "primary.organiser@technexus.local", "Primary Organiser", "organiser", "ADMIN1_TEMP_PASSWORD"),
            ("coorganiser", "co.organiser@technexus.local", "Co-Organiser", "co-organiser", "ADMIN2_TEMP_PASSWORD"),
        ]
        credentials: list[tuple[str, str, str]] = []
        for username, email, full_name, role, env_key in specs:
            if db.query(Administrator).filter(Administrator.username == username).first():
                continue
            password = os.environ.get(env_key) or generate_password()
            db.add(Administrator(
                username=username, email=email, full_name=full_name, role=role,
                password_hash=hash_password(password), must_change_password=True,
            ))
            credentials.append((username, password, role))
        db.commit()
        if credentials:
            path = Path(settings.admin_setup_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                "TECHNEXUS 2026 - PRIVATE ADMINISTRATOR HANDOVER",
                "KEEP THIS FILE SECRET. DO NOT COMMIT IT.",
                "Both passwords must be changed at first login.",
                "",
            ]
            lines += [f"{role.upper()} | username: {username} | temporary password: {password}"
                      for username, password, role in credentials]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            print(f"Created {len(credentials)} administrator account(s).")
            print(f"Private credentials written to: {path}")
        else:
            print("No new administrators created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
