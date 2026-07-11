from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from fastapi import WebSocket

from trump_vs_shakespeare.runtimes.assembly import AssemblyCombatRuntime
from trump_vs_shakespeare.web.rooms import RoomError, RoomManager


class ProbeSocket:
    def __init__(self) -> None:
        self.active_sends = 0
        self.maximum_active_sends = 0
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, payload: dict[str, Any]) -> None:
        self.active_sends += 1
        self.maximum_active_sends = max(self.maximum_active_sends, self.active_sends)
        await asyncio.sleep(0.01)
        self.messages.append(payload)
        self.active_sends -= 1


@pytest.mark.asyncio
async def test_room_broadcasts_are_serialized() -> None:
    manager = RoomManager(AssemblyCombatRuntime.discover(), send_timeout_seconds=1)
    room, _ = await manager.create("local")
    probe = ProbeSocket()
    await manager.register(room, cast(WebSocket, probe))

    await asyncio.gather(manager.broadcast(room), manager.broadcast(room))

    assert probe.maximum_active_sends == 1
    assert len(probe.messages) == 2


@pytest.mark.asyncio
async def test_room_connection_limit_is_enforced() -> None:
    manager = RoomManager(
        AssemblyCombatRuntime.discover(),
        max_sockets_per_room=2,
    )
    room, _ = await manager.create("local")
    first = cast(WebSocket, ProbeSocket())
    second = cast(WebSocket, ProbeSocket())
    third = cast(WebSocket, ProbeSocket())

    await manager.register(room, first)
    await manager.register(room, second)
    with pytest.raises(RoomError, match="too many active connections"):
        await manager.register(room, third)
