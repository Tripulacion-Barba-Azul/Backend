from datetime import date
from fastapi.testclient import TestClient

from App.games.models import Game
from App.players.utils import db_player_2_player_public_info
from main import app
from App.games.services import GameService

client = TestClient(app)

def test_no_action(client: TestClient, seed_games, session):
    
    player_info = {
                "playerName":"Barba Azul",
                "birthDate":date(2000,9,15).strftime("%Y-%m-%d")
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
        
        result = websocket.receive_json()
        assert len(result["players"]) == 2

        response = client.post(f"/play/{game_id}/actions/play-card", json={"playerId": owner_id, "cards": []})
        data = response.json()
    
        assert response.status_code == 200
        assert response.json() == {}