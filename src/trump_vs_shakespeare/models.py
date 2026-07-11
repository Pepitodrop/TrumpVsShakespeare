from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Side = Literal["trump", "shakespeare"]


@dataclass(frozen=True, slots=True)
class Move:
    id: str
    owner: Side
    name: str
    description: str
    damage: int
    cost: int
    accuracy: int
    priority: int
    guard: int = 0
    heal: int = 0

    def public(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class FighterState:
    side: Side
    health: int = 100
    energy: int = 6
    guard: int = 0

    def public(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class MatchState:
    room_code: str
    status: Literal["waiting", "playing", "finished"] = "waiting"
    round: int = 1
    fighters: dict[Side, FighterState] = field(default_factory=dict)
    pending: dict[Side, str] = field(default_factory=dict)
    winner: Side | Literal["draw"] | None = None
    log: list[dict[str, object]] = field(default_factory=list)
