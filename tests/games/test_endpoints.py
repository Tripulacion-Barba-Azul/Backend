from datetime import date
from fastapi.testclient import TestClient



def test_get_games(client: TestClient, seed_games):
    
    response = client.get("/games")
    data = response.json()

    assert response.status_code == 200

    assert isinstance(data, list)
    assert len(data) == 2
    
    game1Rs = data[0]
    game1 = seed_games["games"][0]

    assert game1Rs["gameId"] == game1.id
    assert game1Rs["ownerName"] == game1.owner.name

def test_get_game_by_id_succes(client: TestClient, seed_games):
    response = client.get("/games/1")
    data = response.json()
    game = seed_games["games"][0]
    
    assert response.status_code == 200

    assert data["gameId"] == game.id
    assert data["gameName"] == game.name
    assert data["minPlayers"] == game.min_players
    assert data["maxPlayers"] == game.max_players
    assert data["ownerId"] == game.owner_id
    
    assert len(data["players"]) == 1
    player_re = data["players"][0]
    assert player_re["playerName"] == game.players[0].name
    assert player_re["birthDate"] == game.players[0].birthday.strftime('%Y-%m-%d')


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
    