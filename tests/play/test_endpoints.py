from datetime import date
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_play_card_no_action_success():
    player_info = {
                "playerName":"Barba Azul",
                "birthDate":date(2000,1,1).strftime("%Y-%m-%d")
    }

    game_info = {
                "gameName":"Tripulación de Barba Azul",
                "minPlayers":2,
                "maxPlayers":4
    }
    
    response = client.post(
        "/games", 
        json = {
            "player_info": player_info,
            "game_info": game_info,
        },
    )

    data = response.json()
    game_id = data["gameId"]
    with client.websocket_connect(f"/ws/{game_id}") as websocket:
        result = websocket.receive_json()
        assert result == {"msj" : f"Connected to ws from game {game_id}"}

        new_player_info = {
                    "playerName":"Capitan",
                    "birthDate":date(2001,4,5).strftime("%Y-%m-%d")
        }

        response = client.post(
            f"/games/{game_id}/join", 
            json = new_player_info,
        )