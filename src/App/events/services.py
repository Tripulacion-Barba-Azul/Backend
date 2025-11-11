from sqlalchemy.orm import Session

from App.card.services import CardService
from App.players.models import Player
from App.games.models import Game
from App.events.enums import EventType, Direction
from App.events.models import Event
from App.events.resolvers.factory import get_resolver
from App.card.models import Card
from App.sets.models import DetectiveSet
from App.sets.enums import DetectiveSetType
from App.games.enums import ActionStatus
from App.games.services import GameService
from App.players.enums import TurnAction, TurnStatus
from App.decks.discard_deck_service import DiscardDeckService


class EventManager:

    def __init__(self, db: Session):
        self._db = db
        self._game_service = GameService(db)

    def create(
            self,
            type: EventType,
            game: Game,
            main_player: Player,
            selected_player: Player | None = None,
            played_card: Card | None = None,
            dset: DetectiveSet | None = None,
            cancelable: bool = True,
            resolved: bool = False,
            direction: Direction | None = None
    ) -> Event:
        new_event = Event(
            type=type,
            game=game,
            main_player=main_player,
            selected_player=selected_player,
            played_card=played_card,
            dset=dset,
            cancelable=cancelable,
            resolved=resolved,
            direction=direction
        )
        self._db.add(new_event)
        self._db.flush()
        self._db.commit()
        return new_event


    def get_unresolved_events_by_game(self, game_id: int) -> list[Event]:
        return (
            self._db.query(Event)
            .filter(Event.game_id == game_id)
            .filter(Event.resolved == False)
            .all()
        )

    def get_unresolved_events_by_event_type(self, game_id: int, event_type: EventType) -> list[Event]:
        return (
            self._db.query(Event)
            .filter(Event.game_id == game_id)
            .filter(Event.type == event_type)
            .filter(Event.resolved == False)
            .all()
        )

    
    
    def resolve(self, game_id: int) -> Event | None:
        """
        Procesa los eventos no resueltos de un juego.
        Regla:
        - PLAY_NSF cancela el evento anterior si es cancelable.
        - Si el anterior no es cancelable, el PLAY_NSF no tiene efecto.
        - Si el último evento no es PLAY_NSF, se resuelve normalmente.
        """
        unresolved = self.get_unresolved_events_by_game(game_id)
        unresolved = [
                e for e in unresolved 
                if e.type != EventType.POINT_YOUR_SUSPICIONS_MAIN
            ]
        print(f"este es el tamaño de los eventos sin resolver: {len(unresolved)}")

        if not unresolved:
            return None

        canceled = []
        resolved = []
        main_event = unresolved[0]
        while len(unresolved) > 1 and unresolved[-1].type == EventType.PLAY_NSF:
            last_event = unresolved.pop()
            prev_event = unresolved[-1]

            if prev_event.cancelable:

                prev_event.resolved = True
                last_event.resolved = True
                unresolved.pop()

                if (prev_event.type is EventType.PLAY_SET and 
                    prev_event.dset.type is DetectiveSetType.LADY_EILEEN_BRENT):
                    player = prev_event.main_player
                    dset = prev_event.dset

                    for card in dset.cards:
                        player.cards.append(card)
                    
                    if dset in player.sets:
                        player.sets.remove(dset)               

                    self._db.delete(dset)
                    self._db.flush()
                    self._db.commit()
                

                if (prev_event.type is EventType.PLAY_DETECTIVE and 
                    prev_event.dset.type is DetectiveSetType.LADY_EILEEN_BRENT):
                    player = prev_event.main_player
                    dset = prev_event.dset
                    card = prev_event.played_card
                    
                    player.cards.append(card)
                    dset.cards.remove(card)

                    self._db.flush()
                    self._db.commit()

                if (prev_event.type is EventType.PLAY_CARD and 
                    prev_event.played_card.name in ["Delay the Muderer's Escape","Early Train to Paddington"]):
                    game = prev_event.game
                    card = prev_event.played_card
                    DiscardDeckService(self._db).relate_card_to_discard_deck(game.discard_deck.id, card)
                    self._db.flush()
                    self._db.commit()

                if (prev_event.type is EventType.DISCARD_ETTP):
                    game = prev_event.game
                    card = prev_event.played_card
                    DiscardDeckService(self._db).relate_card_to_discard_deck(game.discard_deck.id, card)
                    prev_event.main_player.turn_status = TurnStatus.DRAWING
                    self._db.flush()

                self._db.commit()
                canceled.append(prev_event.id)
                resolved.append(last_event.id)
            else:
                last_event.resolved = True
                self._db.commit()
                resolved.append(last_event.id)
                break
        
        game = self._game_service.get_by_id(game_id)
        if game:
            game.action_status = ActionStatus.BLOCKED # type: ignore
            
            for p in game.players:
                p.turn_action = TurnAction.NO_ACTION
        
        self._db.flush()
        self._db.commit()

        if unresolved:
            base_event = unresolved[-1]
            resolver = get_resolver(base_event, self._db)
            if not base_event.resolved:
                if resolver:
                    resolver.resolve()
                    base_event.resolved = True
                    self._db.commit()
                else:
                    base_event.resolved = True
                    self._db.commit()

                resolved.append(base_event.id)
            return base_event
        else:
            if main_event.type == EventType.DISCARD_ETTP:
                main_event.main_player.turn_status = TurnStatus.DRAWING
            else:
                main_event.main_player.turn_status = TurnStatus.DISCARDING_OPT
            self._db.flush()
            self._db.commit()
            return None
        """ return {
            "action": "resolved_chain",
            "resolved_events": resolved,
            "canceled_events": canceled
        } """
        
