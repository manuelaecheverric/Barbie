import os
import sys
import time
from pathlib import Path

import jwt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.update({
    "SUPABASE_JWT_SECRET": "test-secret-de-pruebas-con-32-caracteres",
    "SUPABASE_URL": "",
    "SUPABASE_SERVICE_ROLE_KEY": "",
    "DATA_BACKEND": "memory",
    "AGENT_MODE": "mock",
})

from fastapi.testclient import TestClient  # noqa: E402

from services.agent_gateway import get_agent  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from repositories import get_repository  # noqa: E402


def make_token(user_id: str, email: str = "ana@test.com", expired: bool = False) -> str:
    now = int(time.time())
    exp = now - 60 if expired else now + 3600
    payload = {"sub": user_id, "email": email, "aud": "authenticated", "role": "authenticated", "iat": now, "exp": exp}
    return jwt.encode(payload, os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256")


def auth(user_id: str) -> dict:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


@pytest.fixture()
def client():
    get_settings.cache_clear()
    get_repository.cache_clear()
    get_agent.cache_clear()
    from app.main import app

    with TestClient(app) as c:
        yield c
