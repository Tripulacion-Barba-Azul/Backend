from sqlalchemy.orm import Session

from App import players
from App.games.dtos import GameDTO
from App.games.models import Game
from App.players.dtos import PlayerDTO
from App.players.services import PlayerService


class GameService:

    def __init__(self, db: Session):
        self._db = db
        self._player_service = PlayerService(db)


    def create(
            self, 
            player_dto: PlayerDTO,
            game_dto: GameDTO
    ) -> Game:

        if game_dto.max_players < game_dto.min_players:
            raise ValueError("El máximo de jugadores debe ser mayor o igual al mínimo.")

        owner = self._player_service.create(player_dto)
        new_game: Game = Game(
            name=game_dto.name,
            min_players=game_dto.min_players,
            max_players=game_dto.max_players,
            owner=owner,
        )

        self._db.add(new_game)
        self._db.flush()
        self._db.commit()

        return new_game