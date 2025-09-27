from datetime import date
from fastapi.testclient import TestClient


def test_create_game_success(client: TestClient):
    
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

    assert response.status_code == 201
    assert data["gameId"] is not None
    assert data["ownerId"] is not None

def test_create_game_invalid_data(client: TestClient):

    player_info = {
                "playerName":"Barba Azul",
                "birthDate":date(2000,1,1).strftime("%Y-%m-%d")
    }
    game_info = {
                "gameName":"Tripulación de Barba Azul",
                "minPlayers":6,
                "maxPlayers":2
    }
    response = client.post(
        "/games", 
        json = {
            "player_info": player_info,
            "game_info": game_info,
        },
    )

    data = response.json()

    assert response.status_code == 400
    assert response.json()["detail"] == "El máximo de jugadores debe ser mayor o igual al mínimo."
    