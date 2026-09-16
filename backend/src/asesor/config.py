from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

OLLAMA_THINK_LEVELS = frozenset({"low", "medium", "high", "max"})


class AppEnv(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class LlmProviderName(StrEnum):
    GEMINI = "gemini"
    OLLAMA = "ollama"


class EmbeddingsProviderName(StrEnum):
    GEMINI = "gemini"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = AppEnv.DEV
    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:5173"

    database_url: str
    admin_token: str

    llm_provider: LlmProviderName = LlmProviderName.GEMINI
    google_api_key: str | None = None
    google_genai_use_vertexai: bool = False
    ollama_api_base: str | None = None
    # Ollama recorta el contexto en silencio si no se le dice cuánto usar. Con
    # 16 GB de VRAM, 16384 es holgado para un modelo de ~10 GB.
    ollama_context_length: int = Field(default=16384, gt=0)
    # Acepta un nivel ("low", "medium", "high") o un booleano. Sin valor no se
    # manda el parámetro: Ollama responde 400 "does not support thinking" si se
    # le envía a un modelo que no lo tiene.
    # Los modelos pequeños con esta capacidad SOLO llaman tools con el thinking
    # activo, así que no es opcional con ellos; "low" da el mismo tool-calling
    # que true a menos de la mitad de latencia (spec 05 §3, ADR-003).
    ollama_think: bool | str | None = None

    @field_validator("ollama_think", mode="before")
    @classmethod
    def _normalize_think(cls, value: object) -> object:
        """Ollama acepta el booleano o un nivel, pero no la cadena "true".

        Sin esto, OLLAMA_THINK=true llega como el string "true" y la API
        responde: invalid think value (must be high, medium, low, max, true,
        or false).
        """
        if not isinstance(value, str):
            return value

        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        if lowered in OLLAMA_THINK_LEVELS:
            return lowered

        raise ValueError(
            f"OLLAMA_THINK debe ser true, false o un nivel "
            f"({', '.join(sorted(OLLAMA_THINK_LEVELS))}); recibido: {value!r}"
        )

    agent_model: str
    guardrail_model: str
    eval_model: str
    fallback_model: str

    embeddings_provider: EmbeddingsProviderName = EmbeddingsProviderName.GEMINI
    embeddings_model: str
    rag_min_score: float = Field(default=0.55, ge=0.0, le=1.0)

    memory_compaction_token_threshold: int = Field(default=12000, gt=0)
    memory_compaction_keep_recent: int = Field(default=6, gt=0)

    guardrail_canary_token: str
    guardrail_l2_timeout_ms: int = Field(default=1500, gt=0)
    max_tool_calls_per_turn: int = Field(default=4, gt=0)
    enable_fault_injection: bool = False

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    langfuse_project_id: str | None = None
    eval_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def fault_injection_active(self) -> bool:
        return self.enable_fault_injection and self.app_env is AppEnv.DEV

    @property
    def telemetry_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    @model_validator(mode="after")
    def _check_async_driver(self) -> Self:
        if not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the async driver: postgresql+asyncpg://... "
                "(the sync DSN for Alembic is derived in database_url_sync)"
            )
        return self

    @model_validator(mode="after")
    def _check_provider_combination(self) -> Self:
        if self.llm_provider is LlmProviderName.GEMINI:
            if not self.google_genai_use_vertexai and not self.google_api_key:
                raise ValueError(
                    "LLM_PROVIDER=gemini requires GOOGLE_API_KEY "
                    "(or GOOGLE_GENAI_USE_VERTEXAI=true with GCP credentials)"
                )
        elif self.llm_provider is LlmProviderName.OLLAMA:
            if not self.ollama_api_base:
                raise ValueError("LLM_PROVIDER=ollama requires OLLAMA_API_BASE")
            # El prefijo ollama/ puede provocar loops de tool-calling e ignorar
            # contexto; LiteLLM solo trata ollama_chat/ como modelo conversacional.
            if self.agent_model.startswith("ollama/"):
                raise ValueError(
                    "AGENT_MODEL debe usar el prefijo 'ollama_chat/', no 'ollama/' "
                    f"(recibido: {self.agent_model})"
                )
            if not self.agent_model.startswith("ollama_chat/"):
                raise ValueError(
                    "Con LLM_PROVIDER=ollama, AGENT_MODEL debe empezar con 'ollama_chat/' "
                    f"(recibido: {self.agent_model})"
                )

        if self.embeddings_provider is EmbeddingsProviderName.OLLAMA and not self.ollama_api_base:
            raise ValueError("EMBEDDINGS_PROVIDER=ollama requires OLLAMA_API_BASE")

        if (
            self.embeddings_provider is EmbeddingsProviderName.GEMINI
            and not self.google_genai_use_vertexai
            and not self.google_api_key
        ):
            raise ValueError("EMBEDDINGS_PROVIDER=gemini requires GOOGLE_API_KEY")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
