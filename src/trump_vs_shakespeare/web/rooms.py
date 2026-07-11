from __future__ import annotations

import asyncio
import contextlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Literal

from fastapi import WebSocket

from trump_vs_shakespeare.game.engine import GameEngine
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
    rematch_votes: set[Side] = field(default_factory=set)
    broadcast_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: float = field(default_factory=time.monotonic)
    touched_at: float = field(default_factory=time.monotonic)

    def sides_for(self, token: str) -> list[Side]:
        return [side for side, seat_token in self.seats.items() if secrets.compare_digest(seat_token, token)]


class RoomManager:
    def __init__(
        self,
        assembly: AssemblyCombatRuntime,
        ttl_seconds: int = 7200,
        max_rooms: int = 1000,
        max_sockets_per_room: int = 6,
        send_timeout_seconds: float = 3.0,
    ):
        if ttl_seconds < 60:
            raise ValueError("Room TTL must be at least 60 seconds")
        if max_rooms < 1:
            raise ValueError("Maximum rooms must be positive")
        if max_sockets_per_room < 2:
            raise ValueError("Maximum sockets per room must allow both players")
        if send_timeout_seconds <= 0:
            raise ValueError("Socket send timeout must be positive")
        self.assembly = assembly
        self.ttl_seconds = ttl_seconds
        self.max_rooms = max_rooms
        self.max_sockets_per_room = max_sockets_per_room
        self.send_timeout_seconds = send_timeout_seconds
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

    async def restart(self, code: str, token: str) -> bool:
        async with self._lock:
            room = self._get_locked(code)
            sides = room.sides_for(token)
            if not sides:
                raise RoomError("Invalid room token")
            if room.engine.state.status != "finished":
                raise RoomError("A rematch can only be requested after the duel ends")
            room.rematch_votes.update(sides)
            required = set(room.seats)
            restarted = required.issubset(room.rematch_votes)
            if restarted:
                room.engine.restart()
                room.rematch_votes.clear()
            room.touched_at = time.monotonic()
            return restarted

    async def touch(self, code: str, token: str) -> None:
        async with self._lock:
            room = self._get_locked(code)
            if not room.sides_for(token):
                raise RoomError("Invalid room token")
            room.touched_at = time.monotonic()

    async def authorize(self, code: str, token: str) -> tuple[Room, list[Side]]:
        async with self._lock:
            room = self._get_locked(code)
            sides = room.sides_for(token)
            if not sides:
                raise RoomError("Invalid room token")
            room.touched_at = time.monotonic()
            return room, sides

    async def register(self, room: Room, socket: WebSocket) -> None:
        async with self._lock:
            if self.rooms.get(room.code) is not room:
                raise RoomError("Room not found or expired")
            if len(room.sockets) >= self.max_sockets_per_room:
                raise RoomError("This room has too many active connections")
            room.sockets.append(socket)
            room.touched_at = time.monotonic()

    async def disconnect(self, room: Room, socket: WebSocket) -> None:
        async with self._lock:
            if socket in room.sockets:
                room.sockets.remove(socket)
            room.touched_at = time.monotonic()

    async def broadcast(self, room: Room) -> None:
        async with room.broadcast_lock:
            async with self._lock:
                if self.rooms.get(room.code) is not room:
                    return
                sockets = list(room.sockets)
                payload = {
                    "type": "state",
                    "state": room.engine.public_state(),
                    "rematch_votes": sorted(room.rematch_votes),
                }

            stale: list[WebSocket] = []
            for socket in sockets:
                try:
                    await asyncio.wait_for(
                        socket.send_json(payload),
                        timeout=self.send_timeout_seconds,
                    )
                except Exception:
                    stale.append(socket)
            if stale:
                async with self._lock:
                    for socket in stale:
                        if socket in room.sockets:
                            room.sockets.remove(socket)

    async def cleanup(self) -> None:
        async with self._lock:
            expired = self._purge_locked()
        for room in expired:
            for socket in list(room.sockets):
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(socket.close(code=4408), timeout=self.send_timeout_seconds)

    def snapshot_for(self, room: Room, token: str) -> dict[str, object]:
        return self._snapshot(room, room.sides_for(token))

    def _snapshot(self, room: Room, sides: list[Side]) -> dict[str, object]:
        return {
            "mode": room.mode,
            "controlled_sides": sides,
            "rematch_votes": sorted(room.rematch_votes),
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

    def _purge_locked(self) -> list[Room]:
        now = time.monotonic()
        expired = [room for room in self.rooms.values() if now - room.touched_at > self.ttl_seconds]
        for room in expired:
            self.rooms.pop(room.code, None)
        return expired
