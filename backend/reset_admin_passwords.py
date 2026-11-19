"""Emergency recovery: reset both organiser passwords.

Usage (in Render Shell or locally):
    python -m reset_admin_passwords --yes

Generates new secure temporary passwords, forces a password change at next
login and writes the credentials only to the git-ignored .admin_credentials.txt.
"""
from __future__ import annotations

import argparse
import os
import secrets
import string
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Administrator
from app.security import hash_password
from app.services.core import audit

SPECS = [
    ("organiser", "primary.organiser@technexus.local", "Primary Organiser", "organiser"),
    ("coorganiser", "co.organiser@technexus.local", "Co-Organiser", "co-organiser"),
]


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "Tnx!" + "".join(secrets.choice(alphabet) for _ in range(16))


def write_credentials(rows: list[tuple[str, str, str]]) -> Path:
    path = Path(settings.admin_setup_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "TECHNEXUS 2026 - PRIVATE ADMINISTRATOR HANDOVER",
        "KEEP THIS FILE SECRET. DO NOT COMMIT IT.",
        "Both passwords were reset and must be changed at first login.",
        "",
    ]
    lines += [f"{role.upper()} | username: {username} | temporary password: {password}"
              for username, password, role in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Confirm the password reset")
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("Refusing to reset passwords without --yes")

    init_db()
    db = SessionLocal()
    credentials: list[tuple[str, str, str]] = []
    try:
        for username, email, full_name, role in SPECS:
            admin = db.scalar(select(Administrator).where(Administrator.username == username))
            password = generate_password()
            if not admin:
                admin = Administrator(username=username, email=email, full_name=full_name, role=role)
                db.add(admin)
            admin.password_hash = hash_password(password)
            admin.must_change_password = True
            admin.is_active = True
            audit(db, "auth.admin_password.reset", "system", None, "administrator", username)
            credentials.append((username, password, role))
        db.commit()
    finally:
        db.close()

    path = write_credentials(credentials)
    print("Reset both administrator passwords.")
    print(f"Private credentials written to: {path}")
    print("Copy the passwords to a private store now; this container file is ephemeral.")


if __name__ == "__main__":
    main()
