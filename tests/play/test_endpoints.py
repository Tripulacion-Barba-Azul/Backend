
from sqlalchemy.orm import Session

import copy

from datetime import date
from fastapi.testclient import TestClient

from App.decks.discard_deck_service import DiscardDeckService
from App.games.models import Game
from App.players.enums import TurnStatus
from App.card.services import CardService
from App.sets.enums import DetectiveSetType
from App.sets.models import DetectiveSet
from App.players.enums import TurnAction
from App.play.services import PlayService



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

    
def test_select_any_player_endpoint_cards_off_the_table(client: TestClient, seed_game_player2_select_any_player_cards_off_the_table):
    
    game = seed_game_player2_select_any_player_cards_off_the_table[0]
    player = seed_game_player2_select_any_player_cards_off_the_table[1]
    selected_player = seed_game_player2_select_any_player_cards_off_the_table[2]
    
    cards_selected_player = selected_player.cards
    nsf_select_player = 0
    for card in cards_selected_player:
        if card.name == "Not so Fast!":
            nsf_select_player += 1

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
        print(f"WebSocket connection established for player {player.id}")
        response = client.post(
            f"/play/{game.id}/actions/select_any_player", 
            json={
                "playerId": player.id,
                "selectedPlayerId": selected_player.id
                }
        )
        data = response.json()
        print(f"Response data: {data}")
        public_update_received = False
        private_update_received = False

        for i in range(3):
            result = websocket.receive_json()
            print(f"Received event: {result}")
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                public_update_received = True
            elif result.get("event") == "privateUpdate":
                private_update_received = True
            elif result.get("event") == "notifierCardsOffTheTable":
                assert payload["playerId"] == player.id
                assert payload["quantity"] == nsf_select_player
                assert payload["selectedPlayerId"] == selected_player.id



def test_steal_set_endpoint(
        client: TestClient,
        session: Session,
        seed_started_game):
        game = seed_started_game(3)
        player = game.players[1]
        stolen_player = game.players[2]

        cards = list()
        cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))
        cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))

        dset = DetectiveSet(
            type=DetectiveSetType.TOMMY_BERESFORD,
            player=stolen_player,
            cards=cards
            )

        assert player.turn_status == TurnStatus.PLAYING
        
        card = CardService(session).create_event_card("Another Victim","")
        player.cards[0] = card
        
        session.add(dset)
        session.flush()
        session.commit()
     
        with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
            
            response = client.post(
                f"/play/{game.id}/actions/steal-set", 
                json={
                    "playerId": player.id,
                    "stolenPlayerId": stolen_player.id,
                    "setId": dset.id
                    }
            )
            data = response.json()
            assert response.status_code == 200
            
            result = websocket.receive_json()
            result = websocket.receive_json()
            result = websocket.receive_json()
            payload = result.get("payload", {})

            assert result["event"] == "notifierStealSet"
            assert payload["playerId"] == player.id
            assert payload["stolenPlayerId"] == stolen_player.id
            assert payload["setId"] == dset.id

def test_play_card_another_victim_with_no_sets_played(
        client: TestClient,
        session: Session,
        seed_started_game):
        game = seed_started_game(3)
        player = game.players[1]
        stolen_player = game.players[2]

        assert player.turn_status == TurnStatus.PLAYING
        
        card = CardService(session).create_event_card("Another Victim","")
        player.cards[0] = card
        
        session.flush()
        session.commit()
     
        with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
            
            response = client.post(
                f"/play/{game.id}/actions/play-card", 
                json={
                    "playerId": player.id,
                    "cards": [card.id]
                    }
            )
            data = response.json()
            assert response.status_code == 200
            
            result = websocket.receive_json()
            result = websocket.receive_json()
            result = websocket.receive_json()
            

            assert result["event"] == "notifierNoEffect"

            assert player.turn_status == TurnStatus.DISCARDING_OPT
            assert player.turn_action == TurnAction.NO_ACTION

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

def test_reveal_secret_endpoint(client: TestClient, seed_game_player2_reveal):

    game = seed_game_player2_reveal[0]
    player = seed_game_player2_reveal[1]
    other_player = next(p for p in game.players if p.id != player.id)
    secret = other_player.secrets[0]
    
    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
        
        response = client.post(
            f"/play/{game.id}/actions/reveal-secret", 
            json={
                "playerId": player.id,
                "secretId": secret.id,
                "revealedPlayerId": other_player.id
                }
        )
        data = response.json()

        notifier_received = False
        public_update_received = False

        for i in range(2):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "notifierRevealSecret":
                assert payload["playerId"] == player.id
                assert payload["secretId"] == secret.id
                assert payload["selectedPlayerId"] == other_player.id
                notifier_received = True
            elif result.get("event") == "publicUpdate":
                assert payload["actionStatus"] == "blocked"
                players = payload["players"]
                selected_player = next((p for p in players if p["id"] == other_player.id), None)
                secret_rev = next((s for s in selected_player.get("secrets", []) if s["id"] == secret.id), None)
                assert secret_rev["revealed"] is True
                public_update_received = True
        
        assert notifier_received
        assert public_update_received    

    assert response.status_code == 200

def test_hide_secret_endpoint(
        client: TestClient,
        session: Session,
        seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]
    revealed_secret_player = game.players[2]

    cards = list()
    cards.append(CardService(session).create_detective_card("Parker Pyne","",2))
    cards.append(CardService(session).create_detective_card("Parker Pyne","",2))


    assert player.turn_status == TurnStatus.PLAYING
    
    secret = revealed_secret_player.secrets[0]
    secret.revealed = True
    player.cards[0] = cards[0]
    player.cards[1] = cards[1]

    session.flush()
    session.commit()
    PlayService(session).play_set(game, player.id, [cards[0].id, cards[1].id])

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
            
            response = client.post(
                f"/play/{game.id}/actions/hide-secret", 
                json={
                    "playerId": player.id,
                    "secretId": secret.id,
                    "hiddenPlayerId": revealed_secret_player.id
                    }
            )
            data = response.json()
            assert response.status_code == 200
            
            result = websocket.receive_json()

            for s in result["payload"]["players"][2]["secrets"]:
                assert not s["revealed"]


            result = websocket.receive_json()
            result = websocket.receive_json()
            payload = result.get("payload", {})

            assert result["event"] == "notifierHideSecret"
            assert payload["playerId"] == player.id
            assert payload["selectedPlayerId"] == revealed_secret_player.id
            assert payload["secretId"] == secret.id


def test_and_then_there_was_one_more_endpoint(
        client: TestClient,
        session: Session,
        seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]
    stolen_player = game.players[2]
    selected_player = game.players[0]

    secret = stolen_player.secrets[0]
    secret.revealed = True

    card = CardService(session).create_event_card("And There was One More...","")
    player.cards[0] = card

    session.flush()
    session.commit()
    
    PlayService(session).play_card(game, player.id, card.id)

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
            
            response = client.post(
                f"/play/{game.id}/actions/and-then-there-was-one-more", 
                json={
                    "playerId": player.id,
                    "secretId": secret.id,
                    "stolenPlayerId": stolen_player.id,
                    "selectedPlayerId": selected_player.id
                    }
            )
            data = response.json()
            assert response.status_code == 200
            
            result = websocket.receive_json()

            assert len(result["payload"]["players"][0]["secrets"]) == 4
            for s in result["payload"]["players"][0]["secrets"]:
                assert not s["revealed"]
                
            result = websocket.receive_json()
            result = websocket.receive_json()
            payload = result.get("payload", {})

            assert result["event"] == "notifierAndThenThereWasOneMore"
            assert payload["playerId"] == player.id
            assert payload["stolenPlayerId"] == stolen_player.id
            assert payload["giftedPlayerId"] == selected_player.id
            assert payload["secretId"] == secret.id
            assert payload["secretName"] == secret.name

def test_look_into_the_ashes_endpoint(client:TestClient, session:Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]

    card = CardService(session).create_event_card("Look in to the Ashes","")
    player.cards[0] = card

    session.flush()
    session.commit()

    PlayService(session).play_card(game, player.id, card.id)

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.LOOK_INTO_THE_ASHES

    for _ in range(5):
        c = CardService(session).create_event_card("Random Card","")
        DiscardDeckService(session).relate_card_to_discard_deck(game.discard_deck.id, c)
        card_id = c.id

    session.flush()
    session.commit()

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:

        response = client.post(
            f"/play/{game.id}/actions/look-into-the-ashes",
            json = {
                "playerId": player.id,
                "cardId" : card_id,
            }
        )
        data = response.json()

        notifier_received = False
        public_update_received = False
        private_update_received = False

        for i in range(3):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            
            if result.get("event") == "notifierLookIntoTheAshes":

                assert payload["playerId"] == player.id
                notifier_received = True
            elif result.get("event") == "publicUpdate":

                assert payload["actionStatus"] == "blocked"
                public_update_received = True
            elif result.get("event") == "privateUpdate":

                cards = payload.get("cards", [])
                card_ids = [c.get("id") for c in cards]
                assert card_id in card_ids
                private_update_received = True
        
        assert notifier_received
        assert public_update_received   
        assert private_update_received 

    assert response.status_code == 200
    
def test_delay_the_murderers_escape_endpoint(client:TestClient, session:Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]

    assert player.turn_status == TurnStatus.PLAYING

    card = CardService(session).create_event_card("Delay the Muderer's Escape", "")
    player.cards[0] = card

    session.flush()
    session.commit()


    PlayService(session).play_card(game, player.id, card.id)

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.DELAY_THE_MURDERER

    card_ids = []
    cards = []
    for _ in range(5):
        c = CardService(session).create_event_card("Random Card","")
        cards.append(c)
        DiscardDeckService(session).relate_card_to_discard_deck(game.discard_deck.id, c)
        card_ids.append(c.id)

    session.flush()
    session.commit()

    rep_deck_before = len(game.reposition_deck.cards)
    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:

        response = client.post(
            f"/play/{game.id}/actions/delay-the-murderers-escape",
            json = {
                "playerId": player.id,
                "cards" : card_ids,
            }
        )
        data = response.json()

        notifier_received = False
        public_update_received = False
        private_update_received = False

        for i in range(3):
            result = websocket.receive_json()
            payload = result.get("payload", {})

            if result.get("event") == "notifierDelayTheMurderersEscape":

                assert payload["playerId"] == player.id
                notifier_received = True
            elif result.get("event") == "publicUpdate":

                assert payload["actionStatus"] == "blocked"
                assert payload["regularDeckCount"] == rep_deck_before + 5 
                public_update_received = True
            elif result.get("event") == "privateUpdate":
                private_update_received = True

        assert notifier_received
        assert public_update_received   
        assert private_update_received 

    assert response.status_code == 200
