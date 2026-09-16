"""Wiring de la evaluación post-turno (spec 08 S5): que chat/stream de verdad
agende evaluate_turn cuando corresponde muestrear, no solo que
EvaluationService funcione en aislado (eso lo cubre test_evaluation_service).
"""

import json
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from asesor.config import Settings, get_settings
from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.models import EvaluationRow
from asesor.infrastructure.embeddings.fake import FakeEmbeddings
from asesor.infrastructure.llm.fake import FakeAdkLlm, FakeTurn
from asesor.main import create_app
from tests.support.sse import send_message

_JUDGE_VERDICTS = json.dumps(
    {
        "veredictos": [
            {"criterio": "tono_empatico", "cumple": True, "justificacion": "-"},
            {"criterio": "brevedad", "cumple": True, "justificacion": "-"},
            {"criterio": "una_sola_pregunta", "cumple": True, "justificacion": "-"},
            {"criterio": "sin_precios", "cumple": True, "justificacion": "-"},
        ]
    }
)


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    # 1.0: el turno de este test siempre se muestrea, sin depender del azar.
    monkeypatch.setenv("EVAL_SAMPLE_RATE", "1.0")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def app(
    settings: Settings,
    fake_llm: FakeAdkLlm,
    fake_embeddings: FakeEmbeddings,
    clean_database: None,
) -> AsyncIterator[FastAPI]:
    eval_judge = FakeAdkLlm(turns=[FakeTurn(text=_JUDGE_VERDICTS)])
    application = create_app(
        settings, model=fake_llm, embeddings=fake_embeddings, eval_model=eval_judge
    )
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_un_turno_muestreado_persiste_evaluaciones(
    client: AsyncClient, user_id: UUID, session_factory: SessionFactory
) -> None:
    session_response = await client.post("/api/v1/sessions", headers={"X-User-Id": str(user_id)})
    session_response.raise_for_status()
    session_id = session_response.json()["session_id"]

    events = await send_message(client, user_id, session_id, "hola")
    assert any(e.event == "message.completed" for e in events)

    async with session_factory() as db_session:
        rows = (
            await db_session.scalars(
                select(EvaluationRow).where(EvaluationRow.session_id == session_id)
            )
        ).all()

    assert {row.criterio for row in rows} == {
        "tono_empatico",
        "brevedad",
        "una_sola_pregunta",
        "sin_precios",
    }
    assert all(row.score == 1.0 for row in rows)
    assert all(row.message_id for row in rows)
