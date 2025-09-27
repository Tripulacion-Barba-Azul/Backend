from App.games.models import Game
from App.games.schemas import GameInfo


def db_game_2_game_info(db_game: Game) -> GameInfo:
    return GameInfo(
        gameId=db_game.id,
        ownerId=db_game.owner_id,
    )