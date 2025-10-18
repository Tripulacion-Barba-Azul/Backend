from datetime import date
from fastapi.testclient import TestClient
from App.games.enums import GameStatus
from App.websockets import manager



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
                "avatar": 1,
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
                "avatar": 1,
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
                "avatar": 1,
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
    
    with client.websocket_connect(f"/ws/{game_id}/{1}") as websocket:
        

        # Join the created game
        new_player_info = {
                    "playerName":"Capitan",
                    "avatar": 1,
                    "birthDate":date(2001,4,5).strftime("%Y-%m-%d")
        }

        response = client.post(
            f"/games/{game_id}/join", 
            json = new_player_info,
        )
        result = websocket.receive_json()
        assert result == {"event": "player_joined", "player": "Capitan"}

        data = response.json()
        assert response.status_code == 200
        assert data["gameId"] == game_id
        assert data["actualPlayerId"] is not None

def test_join_game_not_found(client: TestClient):

    new_player_info = {
                "playerName":"Capitan",
                "avatar": 1,
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
                "avatar": 1,
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

    # Join the created game
    new_player_info = {
                "playerName":"Capitan",
                "avatar": 1,
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
                "avatar": 2,
                "birthDate":date(1999,12,31).strftime("%Y-%m-%d")
    }

    response = client.post(
        f"/games/{game_id}/join", 
        json = second_player_info,
    )

    data = response.json()

    assert response.status_code == 400
    assert data["detail"] == "El juego ya ha alcanzado el número máximo de jugadores."



def test_start_game_success(client: TestClient, seed_games):
    
    # Create a game to join
    player_info = {
                "playerName":"Barba Azul",
                "avatar": 1,
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
    owner_id = data["ownerId"]
    with client.websocket_connect(f"/ws/{game_id}/{owner_id}") as websocket:
        
        new_player = {
            "playerName": "Barba Negra",
            "avatar": 2,
            "birthDate": date(2001, 4, 5).strftime("%Y-%m-%d")
        }
        client.post(f"/games/{game_id}/join", json=new_player)
        result = websocket.receive_json()
        
        response = client.post(f"/games/{game_id}/start", params={"owner_id": owner_id})
        data = response.json()

        
        public_update_received = False
        private_update_received = False
        
        
        for _ in range(2):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                assert payload["gameStatus"] == GameStatus.IN_PROGRESS.value
                assert len(payload["players"]) == 2
                public_update_received = True
            elif result.get("event") == "privateUpdate":
                # Aquí podrías añadir aserciones para el estado privado si fuera necesario
                private_update_received = True
                assert payload["role"] is not None
                assert len(payload["cards"]) == 6
                assert len(payload["secrets"]) == 3

        assert public_update_received
        assert private_update_received
    
    assert response.status_code == 200
        
    

def test_start_game_not_found(client: TestClient):
    response = client.post("/games/999/start", params={"owner_id": 1})
    detail = response.json()["detail"]
    assert response.status_code == 404
    assert detail == "Se lanza cuando no se encuentra un juego con el id especificado."


def test_exit_game_success(client: TestClient, seed_games):
    # Create a game to join
    player_info = {
                "playerName":"Barba Azul",
                "avatar": 1,
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
    


    new_player_info = {
                "playerName":"Capitan",
                "avatar": 1,
                "birthDate":date(2001,4,5).strftime("%Y-%m-%d")
    }

    response = client.post(
        f"/games/{game_id}/join", 
        json = new_player_info,
    )

    data = response.json()
    player_id = data["actualPlayerId"]
    
    assert response.status_code == 200

    with client.websocket_connect(f"/ws/{game_id}/{player_id}") as websocket:
        
        response = client.post(f"/games/{game_id}/exit", params={"player_id": player_id})
        data = response.json()

        result = websocket.receive_json()
        assert result == {"event": "playerExit", "payload": {"playerId": player_id}}

    assert response.status_code == 200