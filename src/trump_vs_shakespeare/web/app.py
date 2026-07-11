from __future__ import annotations

import asyncio
import contextlib
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from trump_vs_shakespeare import __version__
from trump_vs_shakespeare.game.engine import GameRuleError
from trump_vs_shakespeare.runtimes.assembly import AssemblyCombatRuntime
from trump_vs_shakespeare.web.rooms import RoomError, RoomManager

STATIC_DIR = Path(__file__).resolve().parent / "static"
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
_WS_TOKEN_PREFIX = "tvs-token."


class CreateRoomRequest(BaseModel):
    mode: Literal["local", "online"] = "online"


class JoinRoomRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^[A-Za-z0-9]+$")


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="A room token is required")
    token = authorization.removeprefix("Bearer ").strip()
    if not _TOKEN_PATTERN.fullmatch(token):
        raise HTTPException(status_code=401, detail="Invalid room token")
    return token


def _websocket_token(websocket: WebSocket) -> tuple[str, str] | None:
    offered = websocket.headers.get("sec-websocket-protocol", "")
    for protocol in (item.strip() for item in offered.split(",")):
        if protocol.startswith(_WS_TOKEN_PREFIX):
            token = protocol.removeprefix(_WS_TOKEN_PREFIX)
            if _TOKEN_PATTERN.fullmatch(token):
                return protocol, token
    return None


def create_app() -> FastAPI:
    assembly = AssemblyCombatRuntime.discover()
    manager = RoomManager(
        assembly=assembly,
        ttl_seconds=int(os.getenv("TVS_ROOM_TTL_SECONDS", "7200")),
        max_rooms=int(os.getenv("TVS_MAX_ROOMS", "1000")),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def janitor() -> None:
            while True:
                await asyncio.sleep(60)
                await manager.cleanup()

        task = asyncio.create_task(janitor(), name="room-janitor")
        app.state.rooms = manager
        app.state.assembly = assembly
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="Trump vs. Shakespeare",
        version=__version__,
        docs_url="/api/docs" if os.getenv("TVS_ENABLE_DOCS", "false").casefold() == "true" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    allowed_origins = [
        origin.strip()
        for origin in os.getenv("TVS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self' ws: wss:; "
            "img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/readyz")
    async def ready() -> dict[str, str]:
        return {"status": "ready", "native": assembly.path.name}

    @app.post("/api/rooms")
    async def create_room(payload: CreateRoomRequest) -> dict[str, object]:
        try:
            room, token = await manager.create(payload.mode)
        except RoomError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        snapshot = manager.snapshot_for(room, token)
        return {"room_code": room.code, "token": token, **snapshot}

    @app.post("/api/rooms/join")
    async def join_room(payload: JoinRoomRequest) -> dict[str, object]:
        try:
            room, token = await manager.join(payload.code)
        except RoomError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        await manager.broadcast(room)
        snapshot = manager.snapshot_for(room, token)
        return {"room_code": room.code, "token": token, **snapshot}

    @app.get("/api/rooms/{code}")
    async def room_state(
        code: str,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        token = _bearer_token(authorization)
        try:
            return await manager.state(code, token)
        except RoomError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.websocket("/ws/{code}")
    async def room_socket(websocket: WebSocket, code: str) -> None:
        origin = websocket.headers.get("origin")
        host = websocket.headers.get("host", "")
        same_origins = {f"http://{host}", f"https://{host}"}
        accepted_origins = set(allowed_origins) if allowed_origins else same_origins
        if origin and origin not in accepted_origins:
            await websocket.close(code=4403, reason="Origin is not allowed")
            return

        credentials = _websocket_token(websocket)
        if credentials is None:
            await websocket.close(code=4401, reason="A room token is required")
            return
        selected_protocol, token = credentials

        try:
            room, sides = await manager.connect(code, token, websocket)
        except RoomError as error:
            await websocket.close(code=4403, reason=str(error))
            return

        await websocket.accept(subprotocol=selected_protocol)
        await websocket.send_json(
            {
                "type": "hello",
                "room_code": room.code,
                "mode": room.mode,
                "controlled_sides": sides,
                "rematch_votes": sorted(room.rematch_votes),
                "state": room.engine.public_state(),
            }
        )
        await manager.broadcast(room)
        try:
            while True:
                try:
                    message = await websocket.receive_json()
                except (TypeError, ValueError):
                    await websocket.send_json({"type": "error", "message": "Message must be valid JSON"})
                    continue
                if not isinstance(message, dict):
                    await websocket.send_json({"type": "error", "message": "Message must be a JSON object"})
                    continue
                message_type = message.get("type")
                try:
                    if message_type == "action":
                        move_id = message.get("move_id")
                        if not isinstance(move_id, str) or len(move_id) > 64:
                            raise RoomError("Invalid move id")
                        actor = message.get("actor")
                        if actor is not None and actor not in {"trump", "shakespeare"}:
                            raise RoomError("Invalid actor")
                        await manager.action(room.code, token, move_id, actor)
                    elif message_type == "restart":
                        await manager.restart(room.code, token)
                    elif message_type == "ping":
                        await manager.touch(room.code, token)
                        await websocket.send_json({"type": "pong"})
                        continue
                    else:
                        raise RoomError("Unsupported message type")
                except (RoomError, GameRuleError) as error:
                    await websocket.send_json({"type": "error", "message": str(error)})
                    continue
                await manager.broadcast(room)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await manager.disconnect(room, websocket)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def manifest() -> FileResponse:
        return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker() -> FileResponse:
        return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
