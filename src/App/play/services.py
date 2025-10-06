from sqlalchemy.orm import Session

from App.exceptions import GameNotFoundError, NotPlayersTurnError, PlayerNotFoundError
from App.games.models import Game
from App.players.models import Player
from App.play.enums import TurnStatus

class RoundService:

    def __init__(self, db: Session):
        self._db = db
        
    def no_action(
            self,
            game_id: int,
            player_id: int,
        ) -> None:
        game: Game | None = self._db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")
        
        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        
        player.turn_status = TurnStatus.DISCARDING
        
        self._db.add(player)
        self._db.flush()
        self._db.commit()