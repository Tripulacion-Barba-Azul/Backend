from itertools import count
import pytest
from sqlalchemy.orm import Session

from App.decks.discard_deck_service import DiscardDeckService
from App.events.enums import Direction, EventType
from App.events.models import Event
from App.events.services import EventManager
from App.events.resolvers.factory import get_resolver
from App.events.resolvers.play_detective_resolver import PlayDetectiveResolver
from App.exceptions import InvalididDetectiveSet
from App.games.enums import GameStatus, Winners
from App.games.models import Game
from App.games.services import GameService
from App.play.services import PlayService
from App.players.enums import PlayerRole, TurnStatus
from App.card.services import CardService
from App.players.enums import TurnAction
from App.players.utils import sort_players
from App.sets.enums import DetectiveSetType
from App.sets.models import DetectiveSet
from App.sets.services import DetectiveSetService


def test_discard_card_service(session: Session, seed_game_player2_discard):
    game: Game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    ettp_in_player = any(card.name == "Early Train to Paddington" for card in player.cards)

    cards_id = [card.id for card in player.cards]

    PlayService(session).discard(game, player.id, cards_id)    

    assert len(player.cards) == 0
    if ettp_in_player:
        assert len(game.discard_deck.cards) in [12,17]
    else:
        assert len(game.discard_deck.cards) == 7
        assert player.turn_status == TurnStatus.DRAWING
    
def test_discard_card_service_with_early_train_to_paddington(session: Session, seed_game_player2_discard):
    game: Game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]

    cards_id = [card.id for card in player.cards]

    if any(card.name != "Early Train to Paddington" for card in player.cards):
        card1 = CardService(session).create_event_card("Early Train to Paddington", "")
        player.cards[0] = card1
        cards_id = [card.id for card in player.cards]

    count_ettp = sum(1 for card in player.cards if card.name == "Early Train to Paddington")

    session.flush()
    session.commit()

    PlayService(session).discard(game, player.id, cards_id)

    assert len(player.cards) == 0
    assert count_ettp in [1,2]

def test_draw_card_from_deck_success(session: Session, seed_game_player2_draw):
    game = seed_game_player2_draw[0]
    player = seed_game_player2_draw[1]
    rep_deck_len = len(game.reposition_deck.cards)

    PlayService(session).draw_card_from_deck(game.id, player.id)    

    assert len(player.cards) == 6
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

def test_end_game_win_murderer_for_deck(session: Session, seed_game_player2_discard):
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
    assert game.winners == Winners.MURDERER

def test_end_game_win_murderer_for_social_disgrace(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    detectives = [player for player in game.players if player.role == PlayerRole.DETECTIVE]

    assert game.status != GameStatus.FINISHED

    for detective in detectives:
        detective.in_social_disgrace = True

    game = GameService(session).get_by_id(game.id)
    PlayService(session).end_game(game.id)

    assert game.status == GameStatus.FINISHED
    assert game.winners == Winners.MURDERER

def test_end_game_win_detectives(session: Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]
    murderer = next(player for player in game.players if player.role == PlayerRole.MURDERER)

    for secret in murderer.secrets:
        secret.revealed = True

    PlayService(session).end_game(game.id)
    assert game.status == GameStatus.FINISHED
    assert game.winners == Winners.DETECTIVE

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

    events = EventManager(session).get_unresolved_events_by_game(game.id)

    assert len(player.cards) == 3
    assert new_set in player.sets
    assert len(events) == 1
    assert events[0].type == EventType.PLAY_SET


def test_reveal_secret_service(session: Session, seed_game_player2_reveal):
    game = seed_game_player2_reveal[0]
    player = seed_game_player2_reveal[1]
    other_player = next(p for p in game.players if p.id != player.id)

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.REVEAL_SECRET

    secret = other_player.secrets[0]
    assert not secret.revealed

    PlayService(session).reveal_secret_service(game, player.id, secret.id, other_player.id)

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
    
    event = EventManager(session).get_unresolved_events_by_game(game.id)
    assert len(event) == 1
    assert event[0].type == EventType.PLAY_CARD
    assert len(player.cards) == 5
    assert card in game.discard_deck.cards
    
def test_select_any_player(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    target_player = game.players[2]
    
    card = CardService(session).create_event_card("Cards off the table","")
    player.cards[0] = card

    session.flush()
    session.commit()

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.CARDS_OFF_THE_TABLE

    game, s_player, s_selected_player, event, count_nsf, pysE = PlayService(session).select_any_player(game.id, player.id, target_player.id)

    assert s_player.turn_status == TurnStatus.DISCARDING_OPT
    assert s_player.turn_action == TurnAction.NO_ACTION

    
def test_cards_off_the_table(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    target_player = game.players[2]
    
    card1 = CardService(session).create_event_card("Cards off the table","")
    player.cards[0] = card1
    target_player_cards = target_player.cards
    for card in target_player_cards:
        card = PlayService(session)._player_service.discard_card(target_player.id, card)

    session.add(target_player)
    session.flush()
    session.commit()
    
    target_player.cards = [
    CardService(session).create_event_card("Cards off the table", ""),
    CardService(session).create_instant_card("Not so Fast!", ""),
    CardService(session).create_instant_card("Not so Fast!", ""),
    CardService(session).create_event_card("Cards off the table", ""),
    CardService(session).create_event_card("Cards off the table", ""),
    CardService(session).create_instant_card("Not so Fast!", "")
]

    session.add(target_player)
    session.flush()
    session.commit()

    played_card = PlayService(session).play_card(game, player.id, card1.id)[0]

    assert len(game.discard_deck.cards) == 2
    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.CARDS_OFF_THE_TABLE

    game, s_player, s_selected_player, event, count_nsf, pysE = PlayService(session).select_any_player(game.id, player.id, target_player.id)

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

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.STEAL_SET

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

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.HIDE_SECRET

    hiddenSecret = PlayService(session).hide_secret(
        game,
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

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.ONE_MORE

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

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.LOOK_INTO_THE_ASHES

    card_id = None

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
    player = game.players[1]

    top_five_ids = []
    for _ in range(5):
        c = CardService(session).create_event_card("Random Card","")
        DiscardDeckService(session).relate_card_to_discard_deck(game.discard_deck.id, c)
        top_five_ids.append(c.id)

    session.flush()
    session.commit()

    top_five = PlayService(session).get_top_five_discarded_cards(player, game.id)
    top_five_ids.pop(len(top_five_ids)-1)

    assert len(top_five) <= 5
    for id in top_five_ids:
        assert any(card.id == id for card in top_five)

def test_select_own_secret_case_give(session: Session, seed_started_game):
    game = seed_started_game(3)
    current_turn_player = game.players[1]
    player = game.players[2]
    
    player.turn_action = TurnAction.GIVE_SECRET_AWAY
    current_turn_player.turn_status = TurnStatus.TAKING_ACTION
    secret = player.secrets[0]

    session.flush()
    session.commit()

    PlayService(session).select_own_secret(game, player.id, secret.id)

    assert current_turn_player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION
    assert not secret.revealed
    assert secret in current_turn_player.secrets
    assert secret not in player.secrets

def test_select_own_secret_case_reveal(session: Session, seed_started_game):
    game = seed_started_game(3)
    current_turn_player = game.players[1]
    player = game.players[2]
    
    player.turn_action = TurnAction.REVEAL_OWN_SECRET
    current_turn_player.turn_status = TurnStatus.TAKING_ACTION
    secret = player.secrets[0]

    session.flush()
    session.commit()

    assert not secret.revealed
    PlayService(session).select_own_secret(game, player.id, secret.id)
    
    assert current_turn_player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION
    assert secret.revealed
    assert secret in player.secrets
    
def test_delay_the_murderers_escape_service(session: Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]
    reposition_deck = game.reposition_deck

    assert player.turn_status == TurnStatus.PLAYING

    card = CardService(session).create_event_card("Delay the Muderer's Escape", "")
    player.cards[0] = card

    session.flush()
    session.commit()


    PlayService(session).play_card(game, player.id, card.id)

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.DELAY_THE_MURDERER

    card_ids = []
    cards = []
    for _ in range(5):
        c = CardService(session).create_event_card("Random Card","")
        cards.append(c)
        DiscardDeckService(session).relate_card_to_discard_deck(game.discard_deck.id, c)
        card_ids.append(c.id)

    session.flush()
    session.commit()

    PlayService(session).delay_the_murder_effect(game, player.id, card_ids)


    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION
    assert all(card in reposition_deck.cards for card in cards)
    assert not all(card in game.discard_deck.cards for card in cards)

def test_early_train_to_paddington(session: Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]

    assert player.turn_status == TurnStatus.PLAYING

    card = CardService(session).create_event_card("Early Train to Paddington", "")
    player.cards[0] = card

    session.flush()
    session.commit()

    PlayService(session).play_card(game, player.id, card.id)

    player.turn_status = TurnStatus.TAKING_ACTION
    player.turn_action = TurnAction.EARLY_TRAIN_TO_PADDINGTON

    PlayService(session).early_train_to_paddington(game, player)

    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert len(game.discard_deck.cards) == 7

def test_select_own_card_card_trade(session: Session, seed_started_game):
    game = seed_started_game(3)
    select_player = game.players[2]
    player = game.players[1]
    
    player_card = player.cards[0]
    player.turn_action = TurnAction.CARD_TRADE
    player.turn_status = TurnStatus.TAKING_ACTION
    select_player_card = select_player.cards[0]
    select_player.turn_action = TurnAction.CARD_TRADE

    session.flush()
    session.commit()

    PlayService(session).select_own_card(game, player.id, player_card.id)
    PlayService(session).select_own_card(game, select_player.id, select_player_card.id)

    assert player.turn_action == TurnAction.NO_ACTION
    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert select_player.turn_action == TurnAction.NO_ACTION
    assert player_card in select_player.cards
    assert player_card not in player.cards

def test_select_own_card_dead_card_folly(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    main_player = game.players[1]
    
    direction_event = event_manager.create(
        type=EventType.DEAD_CARD_FOLLY_DIRECTION,
        game=game,
        main_player=main_player,
        direction=Direction.COUNTERCLOCKWISE
    )
    main_player.turn_status = TurnStatus.TAKING_ACTION

    session.flush()
    session.commit()

    for player in game.players:
        card = player.cards[0]
        player.turn_action = TurnAction.DEAD_CARD_FOLLY
        PlayService(session).select_own_card(game, player.id, card.id)

    assert main_player.turn_status == TurnStatus.DISCARDING_OPT
    for player in game.players:
        assert player.turn_action == TurnAction.NO_ACTION

def test_card_trade(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[0]
    player_card = player.cards[0]
    selected_player = game.players[1]
    selected_player_card = selected_player.cards[0]


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

    player.turn_action = TurnAction.CARD_TRADE
    player.turn_status = TurnStatus.TAKING_ACTION
    selected_player.turn_action = TurnAction.CARD_TRADE
    selected_player.turn_status = TurnStatus.WAITING
    session.flush()
    session.commit()

    main_player, selec_player, main_player_card, selec_player_card = PlayService(session).resolver_card_trade(game, [first_event, second_event])

    assert player_card in selected_player.cards
    assert selected_player_card in player.cards
    assert main_player.id == player.id
    assert selec_player.id == selected_player.id
    assert main_player_card.id == player_card.id
    assert selec_player_card.id == selected_player_card.id
    assert main_player_card in selected_player.cards
    assert selec_player_card in player.cards

def test_dead_card_folly(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    players = game.players

    dead_card_events = {}
    debug_cards = {}

    for player in players:
        card = player.cards[0]
        player.turn_action = TurnAction.DEAD_CARD_FOLLY
        dead_card_events[player.id] = event_manager.create(
            type=EventType.DEAD_CARD_FOLLY,
            game=game,
            main_player=player,
            played_card=card
        )
        debug_cards[player.id] = card

    direction_event = event_manager.create(
        type=EventType.DEAD_CARD_FOLLY_DIRECTION,
        game=game,
        main_player=players[0],
        direction=Direction.COUNTERCLOCKWISE
    )
    players[0].turn_status = TurnStatus.TAKING_ACTION

    session.flush()
    session.commit()

    PlayService(session).resolver_dead_card_folly(game, list(dead_card_events.values()))
    
    assert direction_event.resolved
    for event in dead_card_events.values():
        assert event.resolved
    for player in players:
        assert debug_cards[player.id] not in player.cards

def test_select_direction_service(session: Session, seed_started_game):
    game = seed_started_game(3)
    main_player = game.players[1]
    direction_value = "left"

    main_player.turn_action = TurnAction.DEAD_CARD_FOLLY_DIRECTION

    PlayService(session).select_direction(game, main_player.id, direction_value)

    events : list[Event] = session.query(Event).filter_by(
        game_id=game.id,
        type=EventType.DEAD_CARD_FOLLY_DIRECTION,
    ).all()

    for player in game.players:
        assert player.turn_action == TurnAction.DEAD_CARD_FOLLY
    for event in events:
        assert event.direction == Direction.CLOCKWISE
        assert not event.resolved
        
def test_play_detective_resolver_ariadne_oliver(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[2]

    selected_player.cards = [CardService(session).create_detective_card("Hercule Poirot", "", 3) for _ in range(6)]
    cardIds = []
    for i in range(3):
        cardIds.append(selected_player.cards[i].id)
    print(cardIds)

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.HERCULE_POIROT)

    card = CardService(session).create_detective_card("Ariadne Oliver", "", 0)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.REVEAL_OWN_SECRET
    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.NO_ACTION
    assert selected_player.turn_status == TurnStatus.WAITING
    assert selected_player.turn_action == TurnAction.REVEAL_OWN_SECRET

def test_play_detective_resolver_ariadne_oliver_disgrace(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[2]

    selected_player.cards = [CardService(session).create_detective_card("Hercule Poirot", "", 3) for _ in range(6)]
    selected_player.in_social_disgrace = True
    cardIds = []
    for i in range(3):
        cardIds.append(selected_player.cards[i].id)
    print(cardIds)

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.HERCULE_POIROT)

    card = CardService(session).create_detective_card("Ariadne Oliver", "", 0)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.NO_ACTION
    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION
    assert selected_player.turn_status == TurnStatus.WAITING
    assert selected_player.turn_action == TurnAction.NO_ACTION
    
def test_play_detective_resolver_poirot(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[2]

    selected_player.cards = [CardService(session).create_detective_card("Hercule Poirot", "", 3) for _ in range(6)]
    selected_player.in_social_disgrace = True
    cardIds = []
    for i in range(3):
        cardIds.append(selected_player.cards[i].id)
    print(cardIds)

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.HERCULE_POIROT)

    card = CardService(session).create_detective_card("Hercule Poirot", "", 3)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.REVEAL_SECRET
    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.NO_ACTION
    assert selected_player.turn_status == TurnStatus.WAITING
    assert selected_player.turn_action == TurnAction.REVEAL_SECRET

def test_play_detective_resolver_brent(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[2]

    selected_player.cards = [CardService(session).create_detective_card("Lady Eileen Brent", "", 2) for _ in range(6)]
    
    cardIds = []
    for i in range(2):
        cardIds.append(selected_player.cards[i].id)
    print(cardIds)

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.LADY_EILEEN_BRENT)

    card = CardService(session).create_detective_card("Lady Eileen Brent", "", 2)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.SELECT_ANY_PLAYER
    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.NO_ACTION
    assert selected_player.turn_status == TurnStatus.WAITING
    assert selected_player.turn_action == TurnAction.SELECT_ANY_PLAYER

def test_play_detective_resolver_satterquin(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[2]

    selected_player.cards = [CardService(session).create_detective_card("Mr Satterthwaite", "", 2) for _ in range(5)]
    cards = [CardService(session).create_detective_card("Harley Quin", "", 0), CardService(session).create_detective_card("Mr Satterthwaite", "", 2)]
    selected_player.cards = cards
    
    cardIds = [card.id for card in selected_player.cards]
    

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.SATTERTHQUIN)

    card = CardService(session).create_detective_card("Mr Satterthwaite", "", 2)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.SATTERWAITEWILD
    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.NO_ACTION
    assert selected_player.turn_status == TurnStatus.WAITING
    assert selected_player.turn_action == TurnAction.SATTERWAITEWILD

def test_play_detective_resolver_pyne(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[2]

    player.secrets[0].revealed = True

    selected_player.cards = [CardService(session).create_detective_card("Parker Pyne", "", 2) for _ in range(6)]
    
    cardIds = []
    for i in range(2):
        cardIds.append(selected_player.cards[i].id)
    print(cardIds)

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.PARKER_PYNE)

    card = CardService(session).create_detective_card("Parker Pyne", "", 2)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.HIDE_SECRET
    assert player.turn_status == TurnStatus.TAKING_ACTION
    assert player.turn_action == TurnAction.NO_ACTION
    assert selected_player.turn_status == TurnStatus.WAITING
    assert selected_player.turn_action == TurnAction.HIDE_SECRET

def test_play_detective_resolver_pyne_no_secret(session: Session, seed_started_game):

    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[2]

    
    selected_player.cards = [CardService(session).create_detective_card("Parker Pyne", "", 2) for _ in range(6)]
    
    cardIds = []
    for i in range(2):
        cardIds.append(selected_player.cards[i].id)
    print(cardIds)

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.PARKER_PYNE)

    card = CardService(session).create_detective_card("Parker Pyne", "", 2)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.NO_EFFECT
    assert player.turn_status == TurnStatus.DISCARDING_OPT
    assert player.turn_action == TurnAction.NO_ACTION
    assert selected_player.turn_status == TurnStatus.WAITING
    assert selected_player.turn_action == TurnAction.NO_ACTION

def test_play_detective_own_set(session: Session, seed_started_game):
    game = seed_started_game(3)
    player = game.players[1]
    selected_player = game.players[1]

    selected_player.cards = [CardService(session).create_detective_card("Lady Eileen Brent", "", 2) for _ in range(6)]

    cardIds = []
    for i in range(2):
        cardIds.append(selected_player.cards[i].id)
    print(cardIds)

    dset = DetectiveSetService(session).create_detective_set(selected_player.id,
                                                             cardIds,
                                                             DetectiveSetType.LADY_EILEEN_BRENT)

    card = CardService(session).create_detective_card("Lady Eileen Brent", "", 2)
    player.cards[0] = card

    session.flush()
    session.commit()

    event = PlayService(session).add_detective(game, player.id, dset.id, card.id)

    resolver = get_resolver(event, session)
    assert isinstance(resolver, PlayDetectiveResolver)

    turn_action = resolver.resolve()

    assert turn_action == TurnAction.SELECT_ANY_PLAYER
    assert player.turn_status == selected_player.turn_status 
    assert player.turn_action == selected_player.turn_action


def test_recieve_devious_social(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[0]
    player_card = CardService(session).create_devious_card("Social Faux Pas", "")
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


    main_player, selec_player, main_player_card, selec_player_card = PlayService(session).resolver_card_trade(game, [first_event, second_event])

    devious_event = event_manager.get_unresolved_events_by_event_type(game.id, EventType.RECEIVE_DEVIOUS)[0]
    PlayService(session).resolve_devious_event(game, devious_event)

    assert selected_player.turn_action == TurnAction.REVEAL_OWN_SECRET

def test_recieve_devious_blackmailed(session: Session, seed_started_game):
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


    main_player, selec_player, main_player_card, selec_player_card = PlayService(session).resolver_card_trade(game, [first_event, second_event])

    devious_event = event_manager.get_unresolved_events_by_event_type(game.id, EventType.RECEIVE_DEVIOUS)[0]
    PlayService(session).resolve_devious_event(game, devious_event)

    assert player.turn_action == TurnAction.SELECT_HIDDEN_SECRET

def test_select_hidden_secret(session: Session, seed_started_game):
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


    main_player, selec_player, main_player_card, selec_player_card = PlayService(session).resolver_card_trade(game, [first_event, second_event])

    devious_event = event_manager.get_unresolved_events_by_event_type(game.id, EventType.RECEIVE_DEVIOUS)[0]
    PlayService(session).resolve_devious_event(game, devious_event)
    session.flush()
    session.commit()

    assert player.turn_action == TurnAction.SELECT_HIDDEN_SECRET
    player.turn_status = TurnStatus.TAKING_ACTION

    session.flush()
    session.commit()

    PlayService(session).select_hidden_secret(game, selected_player.id, selected_player.secrets[0].id)

    assert player.turn_action == TurnAction.NO_ACTION
    assert player.turn_status == TurnStatus.DISCARDING_OPT


def test_pys_players_selection(session: Session, seed_started_game):
    game = seed_started_game(5)
    main_player = game.players[1]

    event1 = EventManager(session).create(
        type=EventType.POINT_YOUR_SUSPICIONS,
        game=game,
        main_player=main_player,
        selected_player=game.players[2]
    )

    event2 = EventManager(session).create(
        type=EventType.POINT_YOUR_SUSPICIONS,
        game=game,
        main_player=game.players[2],
        selected_player=main_player
    )
    
    event3 = EventManager(session).create(
        type=EventType.POINT_YOUR_SUSPICIONS,
        game=game,
        main_player=game.players[3],
        selected_player=game.players[2]
    )

    event4 = EventManager(session).create(
        type=EventType.POINT_YOUR_SUSPICIONS,
        game=game,
        main_player=game.players[4],
        selected_player=game.players[2]
    )

    event5 = EventManager(session).create(
        type=EventType.POINT_YOUR_SUSPICIONS,
        game=game,
        main_player=game.players[0],
        selected_player=game.players[2]
    )

    participants = PlayService(session).pys_players_selections(game)
    most_selected_players = []
    for p, q in participants:
        if q not in most_selected_players:
            most_selected_players.append(q)
    print(participants)
    print(most_selected_players)

    assert event1.resolved
    assert event2.resolved
    assert event3.resolved
    assert event4.resolved
    assert event5.resolved
    assert game.players[2].id in most_selected_players
    assert len(most_selected_players) == 2
    assert game.players[3].id not in most_selected_players
    assert main_player.id in most_selected_players

def test_resolver_point_your_suspicions(session: Session, seed_started_game):
    game = seed_started_game(5)
    main_player = game.players[1]
    main_player.turn_status = TurnStatus.TAKING_ACTION
    selected_player = game.players[2]

    for player in game.players:
        player.turn_action = TurnAction.POINT_YOUR_SUSPICIONS

    main_event = EventManager(session).create(
        type=EventType.POINT_YOUR_SUSPICIONS_MAIN,
        game=game,
        main_player=main_player,
        selected_player=selected_player
    )

    pysResult = None
    for p in game.players:
        game, player, selected_player, event, cnsf, pysR =PlayService(session).select_any_player(game.id, p.id, selected_player.id)
        pysResult = pysR

    assert selected_player == pysResult
    for player in game.players:
        if player != selected_player:
            assert player.turn_action == TurnAction.NO_ACTION
        else:
            assert player.turn_action == TurnAction.POINT_YOUR_SUSPICIONS_REVEAL

