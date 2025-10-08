from datetime import date
from fastapi.testclient import TestClient

from main import app
from App.games.services import GameService

client = TestClient(app)

def test_no_action(client: TestClient, seed_games):
    
    player_info = {
                "playerName":"Barba Azul",
                "birthDate":date(2000,10,15).strftime("%Y-%m-%d")
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
    owner_id = data["ownerId"]
    with client.websocket_connect(f"/ws/{game_id}/{1}") as websocket:
        
        new_player = {
            "playerName": "Barba Negra",
            "birthDate": date(2001, 4, 5).strftime("%Y-%m-%d"),
        }
        client.post(f"/games/{game_id}/join", json=new_player)
        result = websocket.receive_json()

        
        response = client.post(f"/games/{game_id}/start", params={"owner_id": owner_id})
        data = response.json()
        
        result = websocket.receive_json()
        assert result["playerTurnId"] == owner_id

        response = client.post(f"/play/{game_id}/actions/play-card", json={"playerId": owner_id, "cards": []})
        data = response.json()
        
        result = websocket.receive_json()
        assert result["event"] == "play_card"
        assert result["players"][0]["id"] == owner_id
        assert result["players"][0]["name"] == "Barba Azul"
        assert result["players"][1]["id"] != owner_id
        assert result["players"][1]["name"] == "Barba Negra"
        
    
    assert response.status_code == 200
    assert response.json() == {}