"""Fixtures del evalset: a diferencia del resto de la suite, estos tests
golpean el Ollama real (spec 09, tipo `evalset`, fuera de CI) y necesitan que
el LLM_PROVIDER real sea ollama, no el gemini de prueba que fija
tests/conftest.py para todo lo demas.

Deliberadamente NO usan TEST_DATABASE_URL: quitan DATABASE_URL del entorno
para que Settings caiga a ../.env, la base de datos real de desarrollo, que
ya tiene la KB ingerida con embeddinggemma (ADR-003). Ingerirla de nuevo en
una base de datos de test aislada solo para esto tomaria varios minutos por
corrida sin aportar nada: el evalset no verifica la ingesta, verifica que el
agente real conteste bien. Como efecto secundario, cada corrida deja sesiones
de prueba en esa base, igual que ya dejan las verificaciones manuales de este
proyecto -- no se trunca nada.
"""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from google.adk.models.base_llm import BaseLlm
from google.adk.models.registry import LLMRegistry
from httpx import ASGITransport, AsyncClient

from asesor.config import Settings, get_settings
from asesor.main import create_app

OLLAMA_ENV_OVERRIDES = {
    "LLM_PROVIDER": "ollama",
    "AGENT_MODEL": "ollama_chat/gemma4:12b",
    "GUARDRAIL_MODEL": "ollama_chat/qwen3:4b-instruct",
    "EVAL_MODEL": "ollama_chat/qwen3:4b-instruct",
    "FALLBACK_MODEL": "ollama_chat/llama3.2:3b",
    "EMBEDDINGS_PROVIDER": "ollama",
    "EMBEDDINGS_MODEL": "embeddinggemma:300m",
    "RAG_MIN_SCORE": "0.42",
}

# Un turno con un modelo local en frio puede tardar bastante (ADR-003); un
# timeout de httpx pensado para FakeLlm (5s por defecto) cortaria la conexion
# a mitad de una respuesta real.
REAL_MODEL_TIMEOUT_SECONDS = 180.0


@pytest.fixture
def ollama_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in OLLAMA_ENV_OVERRIDES.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)


@pytest.fixture
def settings(ollama_env: None) -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", timeout=REAL_MODEL_TIMEOUT_SECONDS
    ) as http_client:
        yield http_client


@pytest.fixture
def judge_model(settings: Settings) -> BaseLlm:
    """El mismo mecanismo de resolucion que usa el propio LlmAsJudge de ADK
    (verificado leyendo su fuente, specs/notes/adk-api.md S8): LLMRegistry
    mapea el string de EVAL_MODEL a LiteLlm para un id `ollama_chat/...`, sin
    necesitar ninguna key.
    """
    model_id = settings.eval_model
    llm_class = LLMRegistry().resolve(model_id)
    return llm_class(model=model_id)
