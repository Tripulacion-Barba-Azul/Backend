from fastapi.testclient import TestClient
from App.websockets import manager
from main import app


def test_websocket_send(client: TestClient):

    with client.websocket_connect("/ws/1/1") as websocket:

        import asyncio
        asyncio.run(manager.send_to_player(1, 1, {"test": "data"}))
        data = websocket.receive_json()
        assert data == {"test": "data"}
