from fastapi.testclient import TestClient
from App.websockets import create_manager
from main import app

client = TestClient(app)


def test_websocket():
    create_manager(1)

    client = TestClient(app)
    with client.websocket_connect("/ws/1") as websocket:

        data = websocket.receive_json()
        assert data == {"msj" : "Connected to ws from game 1"}