from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_websocket():
    client = TestClient(app)
    with client.websocket_connect("/ws/1") as websocket:

        data = websocket.receive_json()
        assert data == {"msj" : "Connected to ws from game 1"}