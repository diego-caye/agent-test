import os
from collections.abc import AsyncIterator, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# En esta maquina el 5432 lo ocupa un Postgres nativo, por eso el compose publica
# el 5442. En CI el servicio escucha en el 5432 y se pasa por TEST_DATABASE_URL.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://asesor:asesor@localhost:5442/asesor_test"
)

TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": TEST_DATABASE_URL,
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

for _key, _value in TEST_ENV.items():
    os.environ[_key] = _value

from asesor.config import Settings, get_settings  # noqa: E402
from asesor.infrastructure.db.engine import create_engine  # noqa: E402
from asesor.infrastructure.db.models import Base  # noqa: E402
from asesor.infrastructure.llm.fake import FakeAdkLlm  # noqa: E402
from asesor.main import create_app  # noqa: E402


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)
    yield monkeypatch


@pytest.fixture
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def clean_database(settings: Settings) -> None:
    engine = create_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(text("TRUNCATE TABLE leads"))
    await engine.dispose()


@pytest.fixture
def fake_llm() -> FakeAdkLlm:
    return FakeAdkLlm()


@pytest.fixture
async def app(
    settings: Settings, fake_llm: FakeAdkLlm, clean_database: None
) -> AsyncIterator[FastAPI]:
    application = create_app(settings, model=fake_llm)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
def user_id() -> UUID:
    return uuid4()
