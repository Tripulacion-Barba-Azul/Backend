from App.games.models import Game
from App.games.schemas import GameInfo, GameInfoPlayer
from App.players.models import Player


def db_game_2_game_info(db_game: Game) -> GameInfo:
    return GameInfo(
        gameId=db_game.id,
        ownerId=db_game.owner_id,
    )

def db_game_2_game_info_player(db_game: Game, db_player: Player) -> GameInfoPlayer:
    return GameInfoPlayer(
        gameId=db_game.id,
        actualPlayerId=db_player.id,
    )