from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

from asesor.agent.factory import create_adk_app, create_agent
from asesor.config import Settings
from asesor.infrastructure.llm.fake import FakeAdkLlm


def test_create_adk_app_usa_el_modelo_liviano_para_compactar(settings: Settings) -> None:
    """Sin `summarizer` explícito, ADK usa por defecto el modelo grande del
    propio agente para resumir (agent.canonical_model, verificado leyendo
    google/adk/apps/compaction.py) -- justo cuando la conversación ya es
    larga, el peor momento para sumarle otra llamada al modelo principal.
    Este test fija que `create_adk_app` pasa el modelo liviano en su lugar,
    no que ADK "adivine" el correcto.
    """
    agent_model = FakeAdkLlm(model="agente-grande")
    summarizer_model = FakeAdkLlm(model="modelo-liviano")

    agent = create_agent(
        settings,
        lead_service=None,  # type: ignore[arg-type]
        handoff_service=None,  # type: ignore[arg-type]
        knowledge_service=None,  # type: ignore[arg-type]
        model=agent_model,
    )
    app = create_adk_app(settings, agent, summarizer_model)

    config = app.events_compaction_config
    assert config is not None
    assert isinstance(config.summarizer, LlmEventSummarizer)
    assert config.summarizer._llm is summarizer_model
    assert config.summarizer._llm is not agent_model
    assert config.token_threshold == settings.memory_compaction_token_threshold
    assert config.event_retention_size == settings.memory_compaction_keep_recent
