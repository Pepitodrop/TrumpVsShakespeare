from __future__ import annotations

from fastapi.testclient import TestClient

from trump_vs_shakespeare.web.app import create_app


def test_health_and_local_room_flow() -> None:
    with TestClient(create_app()) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        created = client.post("/api/rooms", json={"mode": "local"})
        assert created.status_code == 200
        payload = created.json()
        assert payload["state"]["status"] == "playing"
        assert set(payload["controlled_sides"]) == {"trump", "shakespeare"}
        state = client.get(
            f"/api/rooms/{payload['room_code']}",
            params={"token": payload["token"]},
        )
        assert state.status_code == 200


def test_online_room_starts_after_join() -> None:
    with TestClient(create_app()) as client:
        created = client.post("/api/rooms", json={"mode": "online"}).json()
        assert created["state"]["status"] == "waiting"
        joined = client.post("/api/rooms/join", json={"code": created["room_code"]})
        assert joined.status_code == 200
        assert joined.json()["state"]["status"] == "playing"
