import os
from collections.abc import Iterator

import pytest

TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://asesor:asesor@localhost:5432/asesor_test",
    "ADMIN_TOKEN": "test-admin-token",
    "LLM_PROVIDER": "gemini",
    "GOOGLE_API_KEY": "test-key",
    "AGENT_MODEL": "gemini-3.8-flash",
    "GUARDRAIL_MODEL": "gemini-3.5-flash-lite",
    "EVAL_MODEL": "gemini-3.5-flash",
    "FALLBACK_MODEL": "gemini-3.7-flash",
    "EMBEDDINGS_PROVIDER": "gemini",
    "EMBEDDINGS_MODEL": "gemini-embedding-001",
    "GUARDRAIL_CANARY_TOKEN": "CANARY-TEST-0001",
}

for key, value in TEST_ENV.items():
    os.environ.setdefault(key, value)


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)
    yield monkeypatch
