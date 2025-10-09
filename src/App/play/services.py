from sqlalchemy.orm import Session

from App import card
from App.card.services import CardService
from App.decks.discard_deck_service import DiscardDeckService
from App.exceptions import GameNotFoundError, NotPlayersTurnError, ObligatoryDiscardError, PlayerNotFoundError
from App.games.models import Game
from App.games.services import GameService
from App.players.models import Player
from App.players.enums import TurnStatus
from App.players.services import PlayerService

class PlayService:

    def __init__(self, db: Session):
        self._db = db
        self._game_service = GameService(db)
        self._player_service = PlayerService(db)
        self._card_service = CardService(db)
        self._discard_deck_service = DiscardDeckService(db)
        
    def no_action(
            self,
            game_id: int,
            player_id: int,
        ) -> Game:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")

        player: Player | None = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        
        player.turn_status = TurnStatus.DISCARDING
        
        self._db.add(player)
        self._db.flush()
        self._db.commit()
        
        return game
    
    def discard(
            self,
            game: Game,
            player_id: int,
            cards_id: list[int]
        ):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_status not in [TurnStatus.DISCARDING, TurnStatus.DISCARDING_OPT]:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")

        if player.turn_status == TurnStatus.DISCARDING and len(cards_id) == 0:
            raise ObligatoryDiscardError(f"Player {player_id} must discard at least one card")

        for card_id in cards_id:
            card = self._card_service.get_card(card_id)
            card = self._player_service.discard_card(player_id, card)
            self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)

        player.turn_status = TurnStatus.DRAWING

        self._db.add(player)
        self._db.flush()
        self._db.commit()