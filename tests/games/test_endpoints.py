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

def test_get_game_by_id_success(client: TestClient, seed_games):
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

def test_get_game_by_id_not_found(client: TestClient, seed_games):
    response = client.get("/games/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": f"Game {id} does not exist"}

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
    
def test_join_game_success(client: TestClient):

    # Create a game to join
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

        # Join the created game
        new_player_info = {
                    "playerName":"Capitan",
                    "birthDate":date(2001,4,5).strftime("%Y-%m-%d")
        }

        response = client.post(
            f"/games/{game_id}/join", 
            json = new_player_info,
        )

        data = response.json()

        assert response.status_code == 200
        assert data["gameId"] == game_id
        assert data["actualPlayerId"] is not None

def test_join_game_not_found(client: TestClient):

    new_player_info = {
                "playerName":"Capitan",
                "birthDate":date(2001,4,5).strftime("%Y-%m-%d")
    }

    response = client.post(
        f"/games/9999/join", 
        json = new_player_info,
    )

    data = response.json()

    assert response.status_code == 404
    assert data["detail"] == "El juego con id 9999 no existe."

def test_join_game_full(client: TestClient):

        # Create a game to join
    player_info = {
                "playerName":"Barba Azul",
                "birthDate":date(2000,1,1).strftime("%Y-%m-%d")
    }

    game_info = {
                "gameName":"Tripulación de Barba Azul",
                "minPlayers":2,
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
    game_id = data["gameId"]
    with client.websocket_connect(f"/ws/{game_id}") as websocket:
        result = websocket.receive_json()
        assert result == {"msj" : f"Connected to ws from game {game_id}"}

        # Join the created game
        new_player_info = {
                    "playerName":"Capitan",
                    "birthDate":date(2001,4,5).strftime("%Y-%m-%d")
        }

        response = client.post(
            f"/games/{game_id}/join", 
            json = new_player_info,
        )

        data = response.json()

        assert response.status_code == 200

        # Try to join the created game with a third player
        second_player_info = {
                    "playerName":"Oficial",
                    "birthDate":date(1999,12,31).strftime("%Y-%m-%d")
        }

        response = client.post(
            f"/games/{game_id}/join", 
            json = second_player_info,
        )

        data = response.json()

        assert response.status_code == 400
        assert data["detail"] == "El juego ya ha alcanzado el número máximo de jugadores."