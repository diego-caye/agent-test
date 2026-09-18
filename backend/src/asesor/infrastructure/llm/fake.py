from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import BaseModel, Field, PrivateAttr

FALLBACK_TEXT = "No tengo más guion, pero sigo aquí para ayudarte 😊"


class FakeTurn(BaseModel):
    """One scripted model turn: either plain text or a single tool call."""

    text: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)


class FakeAdkLlm(BaseLlm):
    """Deterministic BaseLlm for tests: no network.

    Two ways to script it:

    - `rules`: substring of the user message -> turns to play for that message.
      Stateless (the position is derived from the tool responses already in the
      request), so it stays correct under concurrent sessions.
    - `turns`: a global queue, consumed one entry per model call. Simpler, but
      only safe when a single conversation runs at a time.

    ADK calls the model again after every tool response, so a tool exchange
    consumes two entries.
    """

    model: str = "fake-llm"
    turns: list[FakeTurn] = Field(default_factory=list)
    rules: dict[str, list[FakeTurn]] = Field(default_factory=dict)

    _cursor: int = PrivateAttr(default=0)
    _instructions: list[str] = PrivateAttr(default_factory=list)

    @property
    def instructions(self) -> list[str]:
        return list(self._instructions)

    @property
    def calls(self) -> int:
        return self._cursor

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self._instructions.append(_system_instruction_of(llm_request))
        turn = self._pick(llm_request)

        if turn.tool_name:
            call = types.Part.from_function_call(name=turn.tool_name, args=turn.tool_args)
            yield LlmResponse(content=types.Content(role="model", parts=[call]))
            return

        text = turn.text or ""
        if stream:
            for chunk in _chunks(text):
                yield LlmResponse(
                    content=types.Content(role="model", parts=[types.Part.from_text(text=chunk)]),
                    partial=True,
                )

        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part.from_text(text=text)]),
            turn_complete=True,
        )

    def _pick(self, llm_request: LlmRequest) -> FakeTurn:
        if self.rules:
            message, tool_responses_after = _conversation_position(llm_request)
            haystack = message.casefold()
            for pattern, turns in self.rules.items():
                if pattern.casefold() in haystack and turns:
                    index = min(tool_responses_after, len(turns) - 1)
                    return turns[index]

        turn = (
            self.turns[self._cursor]
            if self._cursor < len(self.turns)
            else FakeTurn(text=FALLBACK_TEXT)
        )
        self._cursor += 1
        return turn


def _conversation_position(llm_request: LlmRequest) -> tuple[str, int]:
    """Return the last user message and how many tool responses followed it."""
    contents = list(llm_request.contents or [])

    last_user_index = -1
    message = ""
    for index, content in enumerate(contents):
        if content.role != "user" or not content.parts:
            continue
        text = "".join(part.text or "" for part in content.parts)
        if text:
            last_user_index = index
            message = text

    tool_responses = sum(
        1
        for content in contents[last_user_index + 1 :]
        if any(part.function_response is not None for part in content.parts or [])
    )
    return message, tool_responses


def _chunks(text: str, size: int = 12) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _system_instruction_of(llm_request: LlmRequest) -> str:
    config = llm_request.config
    instruction = getattr(config, "system_instruction", None) if config else None
    if instruction is None:
        return ""
    if isinstance(instruction, str):
        return instruction
    parts = getattr(instruction, "parts", None) or []
    return "".join(part.text or "" for part in parts)
