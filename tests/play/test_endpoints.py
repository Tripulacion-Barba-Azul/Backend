
from sqlalchemy.orm import Session

import copy

from datetime import date
from fastapi.testclient import TestClient

from App.decks.discard_deck_service import DiscardDeckService
from App.events.enums import Direction, EventType
from App.events.services import EventManager
from App.games.models import Game
from App.players.enums import TurnStatus
from App.card.services import CardService
from App.secret.enums import SecretType
from App.sets.enums import DetectiveSetType
from App.sets.models import DetectiveSet
from App.players.enums import TurnAction
from App.play.services import PlayService
from App.sets.services import DetectiveSetService



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
            f"/play/{game.id}/actions/select-any-player", 
            json={
                "playerId": player.id,
                "selectedPlayerId": selected_player.id
                }
        )
        data = response.json()
        
        public_update_received = False
        private_update_received = False

        for i in range(3):
            result = websocket.receive_json()
            
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
        private_update_received = False

        for i in range(3):
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
            elif result.get("event") == "privateUpdate":
                private_update_received = True

        assert notifier_received
        assert public_update_received
        assert private_update_received

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
    

def test_reveal_own_secret_reveal(
        client: TestClient,
        session: Session,
        seed_started_game
    ):
        game = seed_started_game(3)
        player = game.players[1]
        player.turn_status = TurnStatus.TAKING_ACTION
        
        caller_player = game.players[2]
        caller_player.turn_action = TurnAction.REVEAL_OWN_SECRET
        secret = caller_player.secrets[0]

        session.flush()
        session.commit()
     
        with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
            
            response = client.post(
                f"/play/{game.id}/actions/reveal-own-secret", 
                json={
                    "playerId": caller_player.id,
                    "secretId": secret.id
                    }
            )
            data = response.json()
            assert response.status_code == 200
            
            result = websocket.receive_json()
            assert result["event"] == "publicUpdate"
            result = websocket.receive_json()
            assert result["event"] == "privateUpdate"
            result = websocket.receive_json()
            
            assert result["event"] == "notifierRevealSecretForce"
            payload = result["payload"]
            assert payload["playerId"] == player.id
            assert payload["secretId"] == secret.id
            assert payload["selectedPlayerId"] == caller_player.id

            assert caller_player.turn_action == TurnAction.NO_ACTION
            assert player.turn_status == TurnStatus.DISCARDING_OPT
            assert player.turn_action == TurnAction.NO_ACTION

def test_reveal_own_secret_give(
        client: TestClient,
        session: Session,
        seed_started_game
    ):
        game = seed_started_game(3)
        player = game.players[1]
        player.turn_status = TurnStatus.TAKING_ACTION
        
        caller_player = game.players[2]
        caller_player.turn_action = TurnAction.GIVE_SECRET_AWAY
        secret = caller_player.secrets[0]

        session.flush()
        session.commit()
     
        with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
            
            response = client.post(
                f"/play/{game.id}/actions/reveal-own-secret", 
                json={
                    "playerId": caller_player.id,
                    "secretId": secret.id
                    }
            )
            data = response.json()
            assert response.status_code == 200
            
            result = websocket.receive_json()
            assert result["event"] == "publicUpdate"
            result = websocket.receive_json()
            assert result["event"] == "privateUpdate"
            result = websocket.receive_json()
            if result["event"] == "notifierSatterthwaiteWild":
                payload = result["payload"]
                assert payload["playerId"] == player.id
                assert payload["secretId"] == secret.id
                assert payload["secretName"] == secret.name

                assert payload["selectedPlayerId"] == caller_player.id

                assert caller_player.turn_action == TurnAction.NO_ACTION
                assert player.turn_status == TurnStatus.DISCARDING_OPT
                assert player.turn_action == TurnAction.NO_ACTION
            else:
                assert result["event"] == "gameEnded"

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

def test_select_own_card_endpoint_with_dead_card_folly(client:TestClient, session:Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    players = game.players
    main_player = players[1]
    
    for player in players:
        if player.id == main_player.id:
            assert player.turn_status == TurnStatus.PLAYING
        else:
            assert player.turn_status == TurnStatus.WAITING

    direction_event = event_manager.create(
    type=EventType.DEAD_CARD_FOLLY_DIRECTION,
    game=game,
    main_player=main_player,
    direction=Direction.COUNTERCLOCKWISE
    )
    main_player.turn_status = TurnStatus.TAKING_ACTION

    for player in players:
        player.turn_action = TurnAction.DEAD_CARD_FOLLY

    session.flush()
    session.commit()

    counter_post = 0
    receivedNotifier = False
    receivedPublicUpdate = False
    receivedPrivateUpdate = False

    with client.websocket_connect(f"/ws/{game.id}/{main_player.id}") as websocket:
        for player in players:
            response = client.post(
                f"/play/{game.id}/actions/select-own-card",
                json = {
                    "playerId": player.id,
                    "cardId" : player.cards[0].id,
                }
            )
            data = response.json()
            counter_post += 1
            assert response.status_code == 200

        for _ in range(3):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                receivedPublicUpdate = True
            elif result.get("event") == "privateUpdate":
                receivedPrivateUpdate = True
            elif result.get("event") == "notifierDeadCardFolly":
                receivedNotifier = True


    assert counter_post == 3
    assert receivedNotifier
    assert receivedPublicUpdate
    assert receivedPrivateUpdate
    
def test_select_own_card_endpoint_with_card_trade(client:TestClient, session:Session, seed_started_game):
    game = seed_started_game(3)
    main_player = game.players[1]
    selected_player = game.players[2]

    main_player.turn_status = TurnStatus.TAKING_ACTION
    main_player.turn_action = TurnAction.CARD_TRADE
    selected_player.turn_action = TurnAction.CARD_TRADE

    players = [main_player, selected_player]

    session.flush()
    session.commit()

    counter_post = 0
    receivedNotifier = False
    receivedPublicUpdate = False
    receivedPrivateUpdate = False

    with client.websocket_connect(f"/ws/{game.id}/{main_player.id}") as websocket:
        for player in players:
            response = client.post(
                f"/play/{game.id}/actions/select-own-card",
                json = {
                    "playerId": player.id,
                    "cardId" : player.cards[0].id,
                }
            )
            data = response.json()
            counter_post += 1
            assert response.status_code == 200

        for _ in range(3):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                receivedPublicUpdate = True
            elif result.get("event") == "privateUpdate":
                receivedPrivateUpdate = True
            elif result.get("event") == "notifierCardTrade":
                assert payload["playerId"] in [main_player.id, selected_player.id]
                assert payload["cardName"] in [main_player.cards[0].name, selected_player.cards[0].name]
                receivedNotifier = True


    assert counter_post == len(players)
    assert receivedNotifier
    assert receivedPublicUpdate
    assert receivedPrivateUpdate

def test_select_direction_endpoint(client:TestClient, session:Session, seed_started_game):
    game = seed_started_game(3)
    main_player = game.players[1]

    main_player.turn_action = TurnAction.DEAD_CARD_FOLLY_DIRECTION
    session.flush()
    session.commit()

    direction_value = "left"

    receivedPublicUpdate = False
    receivedPrivateUpdate = False
    receivedNotifier = False

    with client.websocket_connect(f"/ws/{game.id}/{main_player.id}") as websocket:
        response = client.post(
            f"/play/{game.id}/actions/select-direction",
            json = {
                "playerId": main_player.id,
                "direction" : direction_value,
            }
        )

        data = response.json()
        assert response.status_code == 200

        for _ in range(3):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                receivedPublicUpdate = True
            elif result.get("event") == "privateUpdate":
                receivedPrivateUpdate = True
            elif result.get("event") == "selectOwnCard":
                receivedNotifier = True

    assert receivedNotifier
    assert receivedPublicUpdate
    assert receivedPrivateUpdate
def test_add_detective_endpoint(client: TestClient, session: Session, seed_started_game):
    """
    Prueba del endpoint /play/{game_id}/actions/add-detective-to-set
    - Prepara un juego con 3 jugadores.
    - Crea un detective set para selected_player.
    - Añade una carta detective al jugador principal y llama al endpoint.
    - Valida que se reciban mensajes websocket (publicUpdate/privateUpdate y notifiers opcionales).
    """
    game = seed_started_game(3)
    player = game.players[1]            # quien añade el detective
    selected_player = game.players[2]   # dueño del set

     
    # Crear set válido para selected_player
    cards_for_set = [
        CardService(session).create_detective_card("Hercule Poirot", "", 3)
        for _ in range(3)
    ]
    for c in cards_for_set:
        CardService(session).relate_card_player(selected_player.id, c.id)

    card_ids = [c.id for c in cards_for_set]

    dset = DetectiveSetService(session).create_detective_set(
        selected_player.id,
        card_ids,
        DetectiveSetType.HERCULE_POIROT
    )

    # Crear la carta detective que player va a añadir
    add_card = CardService(session).create_detective_card("Hercule Poirot", "", 3)
    player.cards[0] = add_card
    CardService(session).relate_card_player(player.id, add_card.id)

    session.flush()
    session.commit()

    private_update_received = False
    public_update_received = False

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
        response = client.post(
            f"/play/{game.id}/actions/add-detective-to-set",
            json={
                "playerId": player.id,
                "setId": dset.id,
                "cardId": add_card.id
            }
        )
        assert response.status_code == 200

        # leer hasta 2 mensajes del websocket enviados por el endpoint/resolve
        for _ in range(2):
            result = websocket.receive_json()
            evt = result.get("event")
            payload = result.get("payload", {})

            if evt == "privateUpdate":

                assert isinstance(payload.get("cards", []), list)
                assert len(payload.get("cards", [])) == 5
                assert add_card not in payload.get("cards", [])
                private_update_received = True
            elif evt == "publicUpdate":
                # payload debe contener el estado público del juego
                assert "players" in payload
                cards = []
                owner = None
                for p in payload.get("players", []):
                    for s in p.get("sets", []):
                        if s.get("setId") == dset.id:
                            owner = p
                            cards = s.get("cards", [])
                    if owner:
                        break
                assert len(cards) == 4  # 3 originales + 1 añadida
                set_card_ids = [c.get("id") for c in cards]
                assert add_card.id in set_card_ids
                public_update_received = True
            

    assert private_update_received, "No se recibió privateUpdate tras add-detective"
    assert public_update_received, "No se recibió publicUpdate tras add-detective"


def test_select_hidden_secret_endpoint(client:TestClient, session:Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[0]
    player_card = CardService(session).create_devious_card("Blackmailed!", "")
    player.cards[0] = player_card
    selected_player = game.players[1]
    selected_player_card = selected_player.cards[5]

    session.flush()
    session.commit()

    first_event = event_manager.create(
        type=EventType.PLAY_CARD,
        game=game,
        main_player=player,
        played_card=player_card,
    )

    second_event = event_manager.create(
        type=EventType.PLAY_CARD,
        game=game,
        main_player=selected_player,
        played_card=selected_player_card
    )


    PlayService(session).resolver_card_trade(game, [first_event, second_event])

    devious_event = event_manager.get_unresolved_events_by_event_type(game.id, EventType.RECEIVE_DEVIOUS)[0]
    PlayService(session).resolve_devious_event(game, devious_event)
    session.flush()
    session.commit()

    assert player.turn_action == TurnAction.SELECT_HIDDEN_SECRET
    player.turn_status = TurnStatus.TAKING_ACTION

    session.flush()
    session.commit()

    with client.websocket_connect(f"/ws/{game.id}/{player.id}") as websocket:
        response = client.post(
            f"/play/{game.id}/actions/select-hidden-secret",
            json = {
                "playerId": selected_player.id,
                "secretId": selected_player.secrets[0].id
            }
        )
        data = response.json()
        assert response.status_code == 200

        for _ in range(3):
            result = websocket.receive_json()
            payload = result.get("payload", {})
            if result.get("event") == "publicUpdate":
                receivedPublicUpdate = True
            elif result.get("event") == "privateUpdate":
                receivedPrivateUpdate = True
            elif result.get("event") == "notifierBlackmailedCard":
                assert payload["playerId"] == selected_player.id
                assert payload["secretName"] == selected_player.secrets[0].name
                assert payload["secretId"] == selected_player.secrets[0].id
                receivedNotifier = True

    assert receivedNotifier
    assert receivedPublicUpdate
    assert receivedPrivateUpdate

    