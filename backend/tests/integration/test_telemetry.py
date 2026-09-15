from asesor.config import Settings
from asesor.infrastructure.telemetry import setup_telemetry, turn_span


def test_turn_span_yields_a_trace_id_without_langfuse_keys(settings: Settings) -> None:
    assert settings.telemetry_enabled is False
    setup_telemetry(settings)

    with turn_span(session_id="s1", user_id="u1", settings=settings) as turn:
        assert len(turn.trace_id) == 32
        assert int(turn.trace_id, 16) != 0
