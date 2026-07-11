from __future__ import annotations

from fastapi.testclient import TestClient

from trump_vs_shakespeare.web.app import create_app


def _authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_and_local_room_flow() -> None:
    with TestClient(create_app()) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        created = client.post("/api/rooms", json={"mode": "local"})
        assert created.status_code == 200
        assert created.headers["cache-control"] == "no-store"
        payload = created.json()
        assert payload["state"]["status"] == "playing"
        assert set(payload["controlled_sides"]) == {"trump", "shakespeare"}

        unauthenticated = client.get(f"/api/rooms/{payload['room_code']}")
        assert unauthenticated.status_code == 401
        query_token = client.get(
            f"/api/rooms/{payload['room_code']}",
            params={"token": payload["token"]},
        )
        assert query_token.status_code == 401
        state = client.get(
            f"/api/rooms/{payload['room_code']}",
            headers=_authorization(payload["token"]),
        )
        assert state.status_code == 200


def test_local_websocket_resolves_a_round_without_exposing_token_in_url() -> None:
    with TestClient(create_app()) as client:
        payload = client.post("/api/rooms", json={"mode": "local"}).json()
        protocol = f"tvs-token.{payload['token']}"
        with client.websocket_connect(
            f"/ws/{payload['room_code']}",
            subprotocols=[protocol],
        ) as socket:
            assert socket.accepted_subprotocol == protocol
            hello = socket.receive_json()
            assert hello["type"] == "hello"
            socket.receive_json()  # Initial authoritative broadcast.

            socket.send_json({"type": "action", "actor": "trump", "move_id": "executive_order"})
            first_lock = socket.receive_json()
            assert first_lock["state"]["pending"]["trump"] is True
            assert first_lock["state"]["round"] == 1

            socket.send_json({"type": "action", "actor": "shakespeare", "move_id": "quill_thrust"})
            resolved = socket.receive_json()
            assert resolved["state"]["round"] == 2
            assert not any(resolved["state"]["pending"].values())


def test_online_room_starts_after_join() -> None:
    with TestClient(create_app()) as client:
        created = client.post("/api/rooms", json={"mode": "online"}).json()
        assert created["state"]["status"] == "waiting"
        joined = client.post("/api/rooms/join", json={"code": created["room_code"]})
        assert joined.status_code == 200
        assert joined.json()["state"]["status"] == "playing"


def test_online_rematch_requires_both_players() -> None:
    with TestClient(create_app()) as client:
        creator = client.post("/api/rooms", json={"mode": "online"}).json()
        opponent = client.post("/api/rooms/join", json={"code": creator["room_code"]}).json()
        room = client.app.state.rooms.rooms[creator["room_code"]]
        room.engine.state.status = "finished"
        room.engine.state.winner = "trump"

        creator_protocol = f"tvs-token.{creator['token']}"
        opponent_protocol = f"tvs-token.{opponent['token']}"
        with client.websocket_connect(
            f"/ws/{creator['room_code']}", subprotocols=[creator_protocol]
        ) as creator_socket:
            creator_socket.receive_json()  # hello
            creator_socket.receive_json()  # initial broadcast
            with client.websocket_connect(
                f"/ws/{creator['room_code']}", subprotocols=[opponent_protocol]
            ) as opponent_socket:
                opponent_socket.receive_json()  # hello
                creator_socket.receive_json()  # second player broadcast
                opponent_socket.receive_json()  # second player broadcast

                creator_socket.send_json({"type": "restart"})
                creator_vote = creator_socket.receive_json()
                opponent_view = opponent_socket.receive_json()
                assert creator_vote["state"]["status"] == "finished"
                assert creator_vote["rematch_votes"] == ["trump"]
                assert opponent_view["rematch_votes"] == ["trump"]

                opponent_socket.send_json({"type": "restart"})
                restarted_for_creator = creator_socket.receive_json()
                restarted_for_opponent = opponent_socket.receive_json()
                assert restarted_for_creator["state"]["status"] == "playing"
                assert restarted_for_opponent["state"]["status"] == "playing"
                assert restarted_for_creator["rematch_votes"] == []
