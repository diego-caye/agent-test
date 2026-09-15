from collections import deque
from collections.abc import Mapping, Sequence


class FakeLlmExhausted(RuntimeError):
    pass


class FakeLlm:
    """Deterministic LLM double for tests: no network, no ADK dependency.

    F2 wraps this in the ADK model adapter once the real signature is verified.
    """

    def __init__(
        self,
        responses: Sequence[str] = (),
        *,
        rules: Mapping[str, str] | None = None,
        fallback: str | None = None,
    ) -> None:
        self._queue: deque[str] = deque(responses)
        self._rules = dict(rules or {})
        self._fallback = fallback
        self._calls: list[str] = []

    @property
    def calls(self) -> list[str]:
        return list(self._calls)

    @property
    def pending(self) -> int:
        return len(self._queue)

    def generate(self, prompt: str) -> str:
        self._calls.append(prompt)

        haystack = prompt.casefold()
        for needle, reply in self._rules.items():
            if needle.casefold() in haystack:
                return reply

        if self._queue:
            return self._queue.popleft()

        if self._fallback is not None:
            return self._fallback

        raise FakeLlmExhausted(
            f"FakeLlm ran out of responses after {len(self._calls)} call(s); "
            "add more responses, a matching rule, or a fallback"
        )

    def reset(self) -> None:
        self._calls.clear()
