from sqlalchemy.orm import Session

from App.events.services import EventManager
from App.card.services import CardService
from App.events.enums import EventType

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
