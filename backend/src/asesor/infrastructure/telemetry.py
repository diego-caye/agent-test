import base64
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from asesor.config import Settings

logger = logging.getLogger("asesor.turn")

_SERVICE_NAME = "asesor-automotriz"


def setup_telemetry(settings: Settings) -> None:
    """Wire OTel to Langfuse. Without keys the provider stays un-exported (no-op)."""
    provider = TracerProvider(resource=Resource.create({"service.name": _SERVICE_NAME}))

    if settings.telemetry_enabled:
        host = (settings.langfuse_host or "https://cloud.langfuse.com").rstrip("/")
        credentials = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}"
        token = base64.b64encode(credentials.encode()).decode()
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=f"{host}/api/public/otel/v1/traces",
                    headers={"Authorization": f"Basic {token}"},
                )
            )
        )

    trace.set_tracer_provider(provider)

    from openinference.instrumentation.google_adk import GoogleADKInstrumentor

    GoogleADKInstrumentor().instrument(tracer_provider=provider)


@dataclass(slots=True)
class TurnTrace:
    trace_id: str
    span: trace.Span

    def set(self, key: str, value: Any) -> None:
        self.span.set_attribute(key, value)


@contextmanager
def turn_span(*, session_id: str, user_id: str, settings: Settings) -> Iterator[TurnTrace]:
    tracer = trace.get_tracer(_SERVICE_NAME)
    with tracer.start_as_current_span("chat.turn") as span:
        context = span.get_span_context()
        trace_id = format(context.trace_id, "032x") if context.trace_id else ""
        span.set_attribute("session_id", session_id)
        span.set_attribute("user_id", user_id)
        span.set_attribute("provider", settings.llm_provider.value)
        span.set_attribute("model", settings.agent_model)
        yield TurnTrace(trace_id=trace_id, span=span)


def log_turn(payload: dict[str, Any]) -> None:
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))
