from sqlalchemy.orm import Session

from App.players.models import Player
from App.games.models import Game
from App.events.enums import EventType
from App.events.models import Event
from App.card.models import Card
from App.sets.models import DetectiveSet


class EventManager:

    def __init__(self, db: Session):
        self._db = db

    def create(
            self,
            type: EventType,
            game: Game,
            main_player: Player,
            selected_player: Player | None = None,
            played_card: Card | None = None,
            dset: DetectiveSet | None = None,
            cancelable: bool = False,
            resolved: bool = False
    ) -> Event:
        new_event = Event(
            type=type,
            game=game,
            main_player=main_player,
            selected_player=selected_player,
            played_card=played_card,
            dset=dset,
            cancelable=cancelable,
            resolved=resolved
        )
        self._db.add(new_event)
        self._db.flush()
        self._db.commit()
        return new_event
