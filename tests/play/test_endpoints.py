import copy
from datetime import date
from fastapi.testclient import TestClient

from App.games.models import Game
from App.players.enums import TurnStatus
from App.players.utils import db_player_2_player_private_info, db_player_2_player_public_info
from main import app
from App.games.services import GameService

client = TestClient(app)

def test_no_action(client: TestClient, seed_games, session):
    
    player_info = {
                "playerName":"Barba Azul",
                "avatar": 1,
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
            "avatar": 2,
            "birthDate": date(2001, 4, 5).strftime("%Y-%m-%d"),
        }
        client.post(f"/games/{game_id}/join", json=new_player)
        
        response = client.post(f"/games/{game_id}/start", params={"owner_id": owner_id})


        response = client.post(f"/play/{game_id}/actions/play-card", json={"playerId": owner_id, "cards": []})
        data = response.json()
    
        assert response.status_code == 200
        assert response.json() == {}


def test_discard_endpoint(client: TestClient, seed_game_player2_discard):

    game: Game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
  
    cards_id = [card.id for card in player.cards[:2]]
  
    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
        response = client.post(
            f"/play/{game.id}/actions/discard", 
            json={
                "playerId": player.id,
                "cards": cards_id
                }
        )
        data = response.json()

        public_update_received = False
        private_update_received = False

        for _ in range(2):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                assert payload["actionStatus"] == "blocked"
                assert payload["discardPileCount"] == 3
                players = payload["players"]         
                player_public = next((p for p in players if p["id"] == player.id), None)
                assert player_public["turnStatus"] == TurnStatus.DRAWING.value
                public_update_received = True
            elif result.get("event") == "privateUpdate":
                assert len(payload["cards"]) == 4
                private_update_received = True
            

        assert public_update_received
        assert private_update_received
    
    assert response.status_code == 200
        


def test_draw_from_regular_deck(client: TestClient, seed_game_player2_draw):

    game = seed_game_player2_draw[0]
    player = seed_game_player2_draw[1]
    rep_deck_count_before = len(game.reposition_deck.cards)
    player_cards_before = len(player.cards)

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
        
        response = client.post(
            f"/play/{game.id}/actions/draw-card", 
            json={
                "playerId": player.id,
                "deck" :"regular",
                "order": None
                }
        )
        data = response.json()

        public_update_received = False
        private_update_received = False

        for i in range(2):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                assert payload["actionStatus"] == "blocked"
                assert payload["regularDeckCount"] == rep_deck_count_before - 1
                players = payload["players"]         
                player_public = next((p for p in players if p["id"] == player.id), None)
                assert player_public["cardCount"] == player_cards_before + 1
                public_update_received = True
            elif result.get("event") == "privateUpdate":
                assert len(payload["cards"]) == 1
                private_update_received = True
        
        assert public_update_received
        assert private_update_received    

    assert response.status_code == 200

def test_draw_from_draft_deck(client: TestClient, seed_game_player2_draw):
    
    game = seed_game_player2_draw[0]
    player = seed_game_player2_draw[1]
    rep_deck_count_before = len(game.reposition_deck.cards)
    card1_before = max(game.draft_deck.cards, key=lambda c: c.order)  # type: ignore
    player_cards_before = len(player.cards)

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
        
        response = client.post(
            f"/play/{game.id}/actions/draw-card", 
            json={
                "playerId": player.id,
                "deck": "draft",
                "order": 3,
            }
                
        )
        data = response.json()

        public_update_received = False
        private_update_received = False

        for i in range(2):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                assert payload["actionStatus"] == "blocked"
                assert payload["regularDeckCount"] == rep_deck_count_before - 1
                players = payload["players"]         
                player_public = next((p for p in players if p["id"] == player.id), None)
                assert player_public["cardCount"] == player_cards_before + 1
                assert payload["draftCards"][2]["id"] != card1_before.id
                assert len(payload["draftCards"]) == 3
                public_update_received = True
            elif result.get("event") == "privateUpdate":
                assert len(payload["cards"]) == 1
                assert payload["cards"][0]["id"] == card1_before.id
                private_update_received = True
        
        assert public_update_received
        assert private_update_received    

    assert response.status_code == 200