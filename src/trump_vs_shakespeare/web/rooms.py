from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass, field
from typing import Literal

from fastapi import WebSocket

from trump_vs_shakespeare.game.engine import GameEngine, GameRuleError
from trump_vs_shakespeare.models import Side
from trump_vs_shakespeare.runtimes.assembly import AssemblyCombatRuntime

RoomMode = Literal["local", "online"]
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class RoomError(ValueError):
    pass


@dataclass(slots=True)
class Room:
    code: str
    mode: RoomMode
    engine: GameEngine
    seats: dict[Side, str] = field(default_factory=dict)
    sockets: list[WebSocket] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    touched_at: float = field(default_factory=time.monotonic)

    def sides_for(self, token: str) -> list[Side]:
        return [side for side, seat_token in self.seats.items() if secrets.compare_digest(seat_token, token)]


class RoomManager:
    def __init__(self, assembly: AssemblyCombatRuntime, ttl_seconds: int = 7200, max_rooms: int = 1000):
        self.assembly = assembly
        self.ttl_seconds = ttl_seconds
        self.max_rooms = max_rooms
        self.rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def create(self, mode: RoomMode) -> tuple[Room, str]:
        if mode not in {"local", "online"}:
            raise RoomError("Mode must be local or online")
        async with self._lock:
            self._purge_locked()
            if len(self.rooms) >= self.max_rooms:
                raise RoomError("The server is at room capacity")
            code = self._new_code()
            token = secrets.token_urlsafe(32)
            engine = GameEngine(code, self.assembly, secrets.randbits(64))
            room = Room(code=code, mode=mode, engine=engine)
            room.seats["trump"] = token
            if mode == "local":
                room.seats["shakespeare"] = token
                engine.start()
            self.rooms[code] = room
            return room, token

    async def join(self, code: str) -> tuple[Room, str]:
        async with self._lock:
            room = self._get_locked(code)
            if room.mode != "online":
                raise RoomError("Local rooms cannot be joined remotely")
            if "shakespeare" in room.seats:
                raise RoomError("This room already has two players")
            token = secrets.token_urlsafe(32)
            room.seats["shakespeare"] = token
            room.touched_at = time.monotonic()
            room.engine.start()
            return room, token

    async def state(self, code: str, token: str) -> dict[str, object]:
        async with self._lock:
            room = self._get_locked(code)
            sides = room.sides_for(token)
            if not sides:
                raise RoomError("Invalid room token")
            room.touched_at = time.monotonic()
            return self._snapshot(room, sides)

    async def action(self, code: str, token: str, move_id: str, actor: str | None = None) -> None:
        async with self._lock:
            room = self._get_locked(code)
            sides = room.sides_for(token)
            if not sides:
                raise RoomError("Invalid room token")
            if room.mode == "local":
                if actor not in sides:
                    raise RoomError("Local action must identify trump or shakespeare")
                side: Side = actor  # type: ignore[assignment]
            else:
                side = sides[0]
            room.engine.submit(side, move_id)
            room.touched_at = time.monotonic()

    async def restart(self, code: str, token: str) -> None:
        async with self._lock:
            room = self._get_locked(code)
            if not room.sides_for(token):
                raise RoomError("Invalid room token")
            room.engine.restart()
            room.touched_at = time.monotonic()

    async def connect(self, code: str, token: str, socket: WebSocket) -> tuple[Room, list[Side]]:
        async with self._lock:
            room = self._get_locked(code)
            sides = room.sides_for(token)
            if not sides:
                raise RoomError("Invalid room token")
            room.sockets.append(socket)
            room.touched_at = time.monotonic()
            return room, sides

    async def disconnect(self, room: Room, socket: WebSocket) -> None:
        async with self._lock:
            if socket in room.sockets:
                room.sockets.remove(socket)
            room.touched_at = time.monotonic()

    async def broadcast(self, room: Room) -> None:
        stale: list[WebSocket] = []
        for socket in list(room.sockets):
            try:
                await socket.send_json({"type": "state", "state": room.engine.public_state()})
            except Exception:
                stale.append(socket)
        if stale:
            async with self._lock:
                for socket in stale:
                    if socket in room.sockets:
                        room.sockets.remove(socket)

    async def cleanup(self) -> None:
        async with self._lock:
            self._purge_locked()

    def snapshot_for(self, room: Room, token: str) -> dict[str, object]:
        return self._snapshot(room, room.sides_for(token))

    def _snapshot(self, room: Room, sides: list[Side]) -> dict[str, object]:
        return {
            "mode": room.mode,
            "controlled_sides": sides,
            "state": room.engine.public_state(),
        }

    def _get_locked(self, code: str) -> Room:
        normalized = code.strip().upper()
        room = self.rooms.get(normalized)
        if room is None:
            raise RoomError("Room not found or expired")
        return room

    def _new_code(self) -> str:
        for _ in range(100):
            code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
            if code not in self.rooms:
                return code
        raise RoomError("Could not allocate a room code")

    def _purge_locked(self) -> None:
        now = time.monotonic()
        expired = [code for code, room in self.rooms.items() if now - room.touched_at > self.ttl_seconds]
        for code in expired:
            del self.rooms[code]
