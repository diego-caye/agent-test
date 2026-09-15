from uuid import UUID

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.apps import App
from google.adk.apps._configs import ResumabilityConfig
from google.adk.apps.app import EventsCompactionConfig
from google.adk.models.base_llm import BaseLlm

from asesor.agent.instruction import render_instruction
from asesor.agent.state import read_dialog_state
from asesor.agent.tools.handoff_tools import make_solicitar_contacto_humano
from asesor.agent.tools.lead_tools import make_guardar_lead
from asesor.application.handoff_service import HandoffService
from asesor.application.lead_service import LeadService
from asesor.config import Settings

APP_NAME = "asesor"
AGENT_NAME = "luis"


def create_agent(
    settings: Settings,
    lead_service: LeadService,
    handoff_service: HandoffService,
    model: str | BaseLlm | None = None,
) -> Agent:
    async def instruction_provider(ctx: ReadonlyContext) -> str:
        dialog = read_dialog_state(ctx.state)
        snapshot = await lead_service.get_snapshot(UUID(ctx.user_id), dialog.stage)
        return render_instruction(snapshot, dialog, settings.guardrail_canary_token)

    return Agent(
        name=AGENT_NAME,
        model=model or settings.agent_model,
        description="Asesor automotriz virtual que orienta sin presionar.",
        instruction=instruction_provider,
        tools=[
            make_guardar_lead(lead_service),
            make_solicitar_contacto_humano(handoff_service),
        ],
    )


def create_adk_app(settings: Settings, agent: Agent) -> App:
    return App(
        name=APP_NAME,
        root_agent=agent,
        events_compaction_config=EventsCompactionConfig(
            token_threshold=settings.memory_compaction_token_threshold,
            event_retention_size=settings.memory_compaction_keep_recent,
        ),
        # Necesario para que la confirmacion de tools pueda pausar y reanudar
        # el turno (spike de F3, ADR-002).
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
