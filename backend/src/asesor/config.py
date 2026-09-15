from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        elif self.llm_provider is LlmProviderName.OLLAMA and not self.ollama_api_base:
            raise ValueError("LLM_PROVIDER=ollama requires OLLAMA_API_BASE")

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
