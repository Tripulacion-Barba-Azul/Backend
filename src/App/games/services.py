from sqlalchemy.orm import Session

from App import players
from App.games.dtos import GameDTO
from App.games.models import Game
from App.games.enums import GameStatus
from App.players.dtos import PlayerDTO
from App.players.services import PlayerService
from App.exceptions import GameNotFoundError, GameFullError, GameAlreadyStartedError


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
    
    def join(
            self, 
            game_id: int, 
            player_dto: PlayerDTO
    ) -> Game:

        game: Game = self._db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise GameNotFoundError(f"El juego con id {game_id} no existe.")
        
        if len(game.players) >= game.max_players:
            raise GameFullError("El juego ya ha alcanzado el número máximo de jugadores.")

        if game.status != GameStatus.WAITING:
            raise GameAlreadyStartedError("No se puede unir a un juego que ya ha comenzado.")

        new_player = self._player_service.create(player_dto)
        game.players.append(new_player)
        game.num_players += 1

        self._db.add(game)
        self._db.flush()
        self._db.commit()

        return game