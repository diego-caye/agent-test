import pytest

from asesor.infrastructure.llm.fake import FakeLlm, FakeLlmExhausted


def test_returns_scripted_responses_in_order() -> None:
    llm = FakeLlm(["uno", "dos"])

    assert llm.generate("a") == "uno"
    assert llm.generate("b") == "dos"
    assert llm.pending == 0


def test_rules_take_precedence_over_queue_and_ignore_case() -> None:
    llm = FakeLlm(["scripted"], rules={"test drive": "derivo"})

    assert llm.generate("Quiero un TEST DRIVE") == "derivo"
    assert llm.generate("otra cosa") == "scripted"


def test_fallback_used_when_queue_is_empty() -> None:
    llm = FakeLlm(fallback="por defecto")

    assert llm.generate("hola") == "por defecto"
    assert llm.generate("hola otra vez") == "por defecto"


def test_raises_when_exhausted_without_fallback() -> None:
    llm = FakeLlm(["solo una"])
    llm.generate("a")

    with pytest.raises(FakeLlmExhausted):
        llm.generate("b")


def test_records_calls() -> None:
    llm = FakeLlm(fallback="x")
    llm.generate("primer prompt")
    llm.generate("segundo prompt")

    assert llm.calls == ["primer prompt", "segundo prompt"]

    llm.reset()
    assert llm.calls == []
