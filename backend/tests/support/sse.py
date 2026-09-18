import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from httpx import AsyncClient


@dataclass(frozen=True, slots=True)
class ReceivedEvent:
    event: str
    data: dict[str, Any]


def parse_sse(body: str) -> list[ReceivedEvent]:
    events: list[ReceivedEvent] = []
    for block in body.split("\n\n"):
        name = ""
        payload = ""
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                payload = line.removeprefix("data: ")
        if name:
            events.append(ReceivedEvent(event=name, data=json.loads(payload) if payload else {}))
    return events


async def send_message(
    client: AsyncClient, user_id: UUID, session_id: str, message: str
) -> list[ReceivedEvent]:
    response = await client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "message": message},
        headers={"X-User-Id": str(user_id)},
    )
    response.raise_for_status()
    return parse_sse(response.text)


def reply_text(events: list[ReceivedEvent]) -> str:
    return "".join(e.data.get("delta", "") for e in events if e.event == "message.delta")


def tool_names(events: list[ReceivedEvent]) -> list[str]:
    return [e.data["name"] for e in events if e.event == "tool.started"]
