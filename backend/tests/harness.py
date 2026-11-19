"""Shared test harness. Sets an isolated database before any app module is imported."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="technexus-e2e-"))
TEST_DB = TEST_ROOT / "technexus-test.db"
CREDENTIALS_FILE = TEST_ROOT / ".admin_credentials.txt"
ADMIN1_TEMP = "TempAdminOne!23"
ADMIN2_TEMP = "TempAdminTwo!23"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "e2e-secret-key-not-for-production-0123456789"
os.environ["ENVIRONMENT"] = "testing"
os.environ["ADMIN1_TEMP_PASSWORD"] = ADMIN1_TEMP
os.environ["ADMIN2_TEMP_PASSWORD"] = ADMIN2_TEMP
os.environ["RATE_LIMIT_PER_MINUTE"] = "100"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.security import rate_limiter  # noqa: E402
import setup_admins  # noqa: E402

STATE: dict = {}


def api() -> TestClient:
    """Independent client with its own cookie jar, sharing the running app."""
    return TestClient(app)


def login_admin(username: str, password: str) -> TestClient:
    client = api()
    response = client.post("/api/auth/admin/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return client


def login_participant(email: str, password: str) -> TestClient:
    client = api()
    response = client.post("/api/auth/participant/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return client


def team_payload(prefix: str, index: int) -> dict:
    return {
        "team_name": f"{prefix} Team {index}",
        "college": "Test College of Engineering",
        "department": "Computer Science",
        "semester": "6",
        "leader": {
            "full_name": f"{prefix} Leader {index}",
            "email": f"{prefix.lower()}.leader{index}@example.com",
            "mobile": f"987650{1000 + index:04d}",
            "password": "StrongPass!23",
        },
        "member": {
            "full_name": f"{prefix} Member {index}",
            "email": f"{prefix.lower()}.member{index}@example.com",
            "mobile": f"987650{2000 + index:04d}",
            "password": "StrongPass!23",
        },
    }


def cleanup() -> None:
    shutil.rmtree(TEST_ROOT, ignore_errors=True)
