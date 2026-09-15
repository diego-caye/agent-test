from typing import Protocol
from uuid import UUID

from asesor.domain.entities import Lead, LeadUpdate


class LeadRepository(Protocol):
    async def get(self, user_id: UUID) -> Lead | None: ...

    async def upsert(self, user_id: UUID, update: LeadUpdate) -> Lead: ...
