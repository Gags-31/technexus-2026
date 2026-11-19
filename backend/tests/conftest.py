from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.harness import (
    ADMIN1_TEMP, ADMIN2_TEMP, CREDENTIALS_FILE, STATE, app, cleanup,
    rate_limiter, setup_admins,
)


@pytest.fixture(scope="session", autouse=True)
def app_environment():
    with TestClient(app) as root:
        STATE["root"] = root
        original = setup_admins.settings.admin_setup_file
        setup_admins.settings.admin_setup_file = str(CREDENTIALS_FILE)
        try:
            setup_admins.main()
        finally:
            setup_admins.settings.admin_setup_file = original
        yield
    cleanup()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()
