from sqlalchemy.orm import Session

from App.events.resolvers.factory import get_resolver
from App.events.resolvers.play_detective_resolver import PlayDetectiveResolver
from App.events.services import EventManager
from App.card.services import CardService
from App.events.enums import EventType
from App.play.services import PlayService
from App.players.enums import TurnAction, TurnStatus
from App.sets.enums import DetectiveSetType
from App.sets.services import DetectiveSetService

def test_create_event(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[1]

    card = CardService(session).create_event_card("Another Victim","")
    player.cards[0] = card
    
    session.flush()
    session.commit()

    new_event = event_manager.create(
        type=EventType.PLAY_CARD,
        game=game,
        main_player=player,
        played_card=card
    )

    event = game.events[0]
    assert event.main_player_id == player.id
    assert event.type == EventType.PLAY_CARD
    assert event.played_card_id == card.id
    assert event.selected_player_id is None
    assert event.dset_id is None


def test_get_unresolved_events(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[0]
    other_players = game.players[1:]

    for i in range(2):
        player.cards[i] = CardService(session).create_event_card("Another Victim","")

    for p in other_players:
        p.cards[0] = CardService(session).create_instant_card("Not so Fast!", "")
    
    session.flush()
    session.commit()

    resolved_event = event_manager.create(
        type=EventType.PLAY_CARD,
        game=game,
        main_player=player,
        played_card=player.cards[0],
        resolved = True
    )

    first_event = event_manager.create(
        type=EventType.PLAY_CARD,
        game=game,
        main_player=player,
        played_card=player.cards[1]
    )

    second_event = event_manager.create(
        type=EventType.PLAY_NSF,
        game=game,
        main_player=other_players[0],
        played_card=other_players[0].cards[0]
    )
    third_event = event_manager.create(
        type=EventType.PLAY_NSF,
        game=game,
        main_player=other_players[1],
        played_card=other_players[1].cards[0]
    )

    unresolved_events = event_manager.get_unresolved_events_by_game(game.id)

    assert len(unresolved_events) == 3
    assert unresolved_events[0] == first_event
    assert unresolved_events[1] == second_event
    assert unresolved_events[2] == third_event

def test_get_unresolved_events_by_event_type(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[0]
    other_players = game.players[1:]

    for i in range(2):
        player.cards[i] = CardService(session).create_event_card("Another Victim","")

    for p in other_players:
        p.cards[0] = CardService(session).create_instant_card("Not so Fast!", "")
    
    session.flush()
    session.commit()

    resolved_event = event_manager.create(
        type=EventType.CARD_TRADE,
        game=game,
        main_player=player,
        played_card=player.cards[0],
        resolved = True
    )

    first_event = event_manager.create(
        type=EventType.CARD_TRADE,
        game=game,
        main_player=player,
        played_card=player.cards[1]
    )

    second_event = event_manager.create(
        type=EventType.DEAD_CARD_FOLLY,
        game=game,
        main_player=other_players[0],
        played_card=other_players[0].cards[0]
    )
    third_event = event_manager.create(
        type=EventType.DEAD_CARD_FOLLY,
        game=game,
        main_player=other_players[1],
        played_card=other_players[1].cards[0]
    )

    event : list[EventType] = [EventType.CARD_TRADE, EventType.DEAD_CARD_FOLLY]
    for event_type in event:
        if event_type == EventType.CARD_TRADE:
            unresolved_events = event_manager.get_unresolved_events_by_event_type(game.id, EventType.CARD_TRADE)
            assert len(unresolved_events) == 1
            assert unresolved_events[0] == first_event
        elif event_type == EventType.DEAD_CARD_FOLLY:
            unresolved_events = event_manager.get_unresolved_events_by_event_type(game.id, EventType.DEAD_CARD_FOLLY)
            assert len(unresolved_events) == 2
            assert unresolved_events[0] == second_event
            assert unresolved_events[1] == third_event

def test_resolve_canceled_effect(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[1]
    player2 = game.players[0]
    number_remaining_cards = game.reposition_deck.number_of_cards

    player.cards[0] = CardService(session).create_event_card("Early Train to Paddington","")
    
    session.flush()
    session.commit()


    first_event = event_manager.create(
        type=EventType.PLAY_CARD,
        game=game,
        main_player=player,
        played_card=player.cards[0],
    )

    second_event = event_manager.create(
        type=EventType.PLAY_NSF,
        game=game,
        main_player=player2,
        played_card=player2.cards[5] # PLAY NOT SO FAST
    )

    session.flush()
    session.commit()


    event_manager.resolve(game.id)

    unresolved_events = event_manager.get_unresolved_events_by_game(game.id)
    
    assert len(unresolved_events) == 0
    assert game.reposition_deck.number_of_cards == number_remaining_cards


def test_resolve_double_nsf(session: Session, seed_started_game):
    event_manager = EventManager(session)
    game = seed_started_game(3)
    player = game.players[1]
    player2 = game.players[0]
    player3 = game.players[2]
    number_remaining_cards = game.reposition_deck.number_of_cards
    print(number_remaining_cards)

    player.cards[5] = CardService(session).create_event_card("Early Train to Paddington","")
    
    session.flush()
    session.commit()


    first_event = event_manager.create(
        type=EventType.PLAY_CARD,
        game=game,
        main_player=player,
        played_card=player.cards[5],
    )

    second_event = event_manager.create(
        type=EventType.PLAY_NSF,
        game=game,
        main_player=player2,
        played_card=player2.cards[5] # sixth card always a NSF
    )

    third_event = event_manager.create(
        type=EventType.PLAY_NSF,
        game=game,
        main_player=player3,
        played_card=player3.cards[5]
    )

    session.flush()
    session.commit()


    event_manager.resolve(game.id)

    unresolved_events = event_manager.get_unresolved_events_by_game(game.id)
    
    assert len(unresolved_events) == 0
    assert game.reposition_deck.number_of_cards == number_remaining_cards - 6


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
    