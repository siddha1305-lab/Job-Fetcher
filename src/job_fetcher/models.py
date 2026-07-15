from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Job:
    company: str
    title: str
    locations: list[str]
    url: str
    source_firms: list[str]
    logo_url: str | None = None
    posted_at: str | None = None
    remote: bool = False
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Board:
    name: str
    url: str
    provider: str
    board_id: str | None = None
