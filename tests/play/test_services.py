from sqlalchemy.orm import Session

from App.decks.discard_deck_service import DiscardDeckService
from App.games.enums import GameStatus
from App.games.models import Game
from App.games.services import GameService
from App.play.services import PlayService
from App.players.enums import TurnStatus
from App.card.services import CardService
from App.players.enums import TurnAction
from App.sets.enums import DetectiveSetType
from App.sets.models import DetectiveSet


def test_discard_card_service(session: Session, seed_game_player2_discard):
    game: Game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]

    cards_id = [card.id for card in player.cards]

    PlayService(session).discard(game, player.id, cards_id)    

    assert len(player.cards) == 0
    assert player.turn_status == TurnStatus.DRAWING
    assert len(game.discard_deck.cards) == 7

def test_draw_card_from_deck_success(session: Session, seed_game_player2_draw):
    game = seed_game_player2_draw[0]
    player = seed_game_player2_draw[1]
    rep_deck_len = len(game.reposition_deck.cards)

    PlayService(session).draw_card_from_deck(game.id, player.id)    

    assert len(player.cards) == 1
    assert player.turn_status == TurnStatus.DRAWING
    assert rep_deck_len - 1 == len(game.reposition_deck.cards)

def test_draw_card_from_deck_6_cards_error(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]

    PlayService(session).discard(game, player.id, [card.id])
    
    PlayService(session).draw_card_from_deck(game.id, player.id)    

    try:
        PlayService(session).draw_card_from_deck(game.id, player.id)    
        assert False
    except Exception as e:
        assert str(e) == f"Player {player.id} already has 6 cards"

def test_end_turn_success(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]

    PlayService(session).discard(game, player.id, [card.id])
    PlayService(session).draw_card_from_deck(game.id, player.id)
    
    PlayService(session).end_turn(game.id, player.id) 

    assert player.turn_status == TurnStatus.WAITING
    assert game.turn_number == 2

def test_end_turn_need_six_cards_error(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]
    card2 = player.cards[1]

    PlayService(session).discard(game, player.id, [card.id, card2.id])

    PlayService(session).draw_card_from_deck(game.id, player.id)
    
    try:
        PlayService(session).end_turn(game.id, player.id) 
        assert False
    except Exception as e:
        assert str(e) == f"Player {player.id} needs to have six cards to end turn"

def test_end_game_not_finished(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]

    PlayService(session).discard(game, player.id, [card.id])
    PlayService(session).draw_card_from_deck(game.id, player.id)
    
    PlayService(session).end_turn(game.id, player.id) 

    assert player.turn_status == TurnStatus.WAITING
    assert game.turn_number == 2

    PlayService(session).end_game(game.id)
    assert game.status == GameStatus.IN_PROGRESS
    
def test_end_game_(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]

    PlayService(session).discard(game, player.id, [card.id])
    PlayService(session).draw_card_from_deck(game.id, player.id)
    
    PlayService(session).end_turn(game.id, player.id) 

    assert player.turn_status == TurnStatus.WAITING
    assert game.turn_number == 2

    game = GameService(session).get_by_id(game.id)
    game.reposition_deck.cards = []
    session.add(game)
    session.flush()
    session.commit()

    PlayService(session).end_game(game.id)
    assert game.status == GameStatus.FINISHED

def test_play_set(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]

    assert player.turn_status == TurnStatus.PLAYING

    card_ids = []
    for i in range(3):
        card = CardService(session).create_detective_card("Hercule Poirot","",3)
        player.cards[i] = card
        card_ids.append(card.id)

    session.flush()
    session.commit()

    new_set = PlayService(session).play_set(game, player.id, card_ids)

    assert len(player.cards) == 3
    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.REVEAL_SECRET
    assert new_set in player.sets


def test_reveal_secret_service(session: Session, seed_game_player2_reveal):
    game = seed_game_player2_reveal[0]
    player = seed_game_player2_reveal[1]
    other_player = next(p for p in game.players if p.id != player.id)

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.REVEAL_SECRET

    secret = other_player.secrets[0]
    assert not secret.revealed

    PlayService(session).reveal_secret_service(player.id, secret.id, other_player.id)

    assert secret.revealed
    assert player.turn_action == TurnAction.NO_ACTION

def test_play_card(session: Session, seed_started_game):


    game = seed_started_game(3)
    player = game.players[1]

    assert player.turn_status == TurnStatus.PLAYING

    card = CardService(session).create_event_card("Another Victim","")
    player.cards[0] = card
    
    session.flush()
    session.commit()

    card, event = PlayService(session).play_card(game, player.id, card.id)
    
    assert len(player.cards) == 5
    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert event == TurnAction.NO_EFFECT
    assert card in game.discard_deck.cards
    
def test_select_any_player(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    target_player = game.players[2]
    
    card = CardService(session).create_event_card("Cards off the table","")
    player.cards[0] = card

    session.flush()
    session.commit()

    played_card = PlayService(session).play_card(game, player.id, card.id)[0]

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.CARDS_OFF_THE_TABLE

    game, s_player, s_selected_player = PlayService(session).select_any_player(game.id, player.id, target_player.id)

    assert s_player.turn_status == TurnStatus.TAKING_ACTION
    assert s_player.turn_action == TurnAction.CARDS_OFF_THE_TABLE
    assert s_selected_player.turn_status == TurnStatus.WAITING
    
def test_cards_off_the_table(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    target_player = game.players[2]
    
    card1 = CardService(session).create_event_card("Cards off the table","")
    player.cards[0] = card1
    target_player.cards[0] = CardService(session).create_event_card("Cards off the table","")
    target_player.cards[1] = CardService(session).create_instant_card("Not so Fast!", "")
    target_player.cards[2] = CardService(session).create_event_card("Cards off the table","")
    target_player.cards[3] = CardService(session).create_instant_card("Not so Fast!", "")
    target_player.cards[4] = CardService(session).create_instant_card("Not so Fast!", "")
    target_player.cards[5] = CardService(session).create_event_card("Cards off the table","")

    session.add(player)
    session.add(target_player)
    session.flush()
    session.commit()

    played_card = PlayService(session).play_card(game, player.id, card1.id)[0]

    assert len(game.discard_deck.cards) == 2
    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.CARDS_OFF_THE_TABLE

    game, s_player, s_selected_player = PlayService(session).select_any_player(game.id, player.id, target_player.id)

    assert s_player.turn_status == TurnStatus.TAKING_ACTION
    assert s_player.turn_action == TurnAction.CARDS_OFF_THE_TABLE
    assert s_selected_player.turn_status == TurnStatus.WAITING

    count_nsf = PlayService(session).cards_off_the_tables(game, player, target_player)

    assert len(s_player.cards) == 5
    assert count_nsf == 3
    assert len(game.discard_deck.cards) == count_nsf + 2
    assert s_player.turn_status == TurnStatus.DISCARDING_OPT
    assert s_player.turn_action == TurnAction.NO_ACTION
    assert s_selected_player.turn_status == TurnStatus.WAITING
  
    

def test_steal_set(session: Session, seed_started_game):
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
    
    PlayService(session).play_card(game, player.id, card.id)

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.STEAL_SET

    stolen_set = PlayService(session).steal_set(
        player.id,
        stolen_player.id,
        dset.id
    )

    assert stolen_set in player.sets
    assert stolen_set not in stolen_player.sets
    assert stolen_set == dset
    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION

def test_hide_secret(session: Session, seed_started_game):
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

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.HIDE_SECRET

    hiddenSecret = PlayService(session).hide_secret(
        player.id,
        secret.id,
        revealed_secret_player.id
    )

    assert secret == hiddenSecret
    assert not revealed_secret_player.secrets[0].revealed
    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION


def test_and_then_there_was_one_more_service(session: Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]
    stolen_player = game.players[2]
    selected_player = game.players[0]

    assert player.turn_status == TurnStatus.PLAYING
    
    secret = stolen_player.secrets[0]
    secret.revealed = True

    card = CardService(session).create_event_card("And There was One More...","")
    player.cards[0] = card

    session.flush()
    session.commit()
    
    PlayService(session).play_card(game, player.id, card.id)

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.ONE_MORE

    stolen_secret = PlayService(session).and_then_there_was_one_more_effect( 
                                           player.id,
                                           secret.id,
                                           stolen_player.id,
                                           selected_player.id)
    
    assert secret == stolen_secret
    assert secret not in stolen_player.secrets
    assert len(selected_player.secrets) == 4
    assert not secret.revealed
    assert secret in selected_player.secrets

def test_look_into_the_ashes_effect(session: Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]

    assert player.turn_status == TurnStatus.PLAYING

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

    taken_card = PlayService(session).look_into_the_ashes_effect(game, player.id, card_id)

    assert taken_card in player.cards
    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION
    assert taken_card not in game.discard_deck.cards
    assert taken_card.id == card_id
    
def test_get_top_five_discarded_cards(session: Session, seed_started_game):
    game = seed_started_game(3)


    top_five_ids = []
    for _ in range(5):
        c = CardService(session).create_event_card("Random Card","")
        DiscardDeckService(session).relate_card_to_discard_deck(game.discard_deck.id, c)
        top_five_ids.append(c.id)

    session.flush()
    session.commit()

    top_five = PlayService(session).get_top_five_discarded_cards(game.id)

    assert len(top_five) == 5
    for i in range(5):
        assert top_five[i].id == top_five_ids[4 - i] 