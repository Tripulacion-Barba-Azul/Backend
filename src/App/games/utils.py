from App.games.models import Game
from App.games.schemas import GameInfo, GameLobbyInfo


def db_game_2_game_info(db_game: Game) -> GameInfo:
    return GameInfo(
        gameId=db_game.id,
        ownerId=db_game.owner_id,
    )

def db_game_2_game_lobby_info(db_game: Game) -> GameLobbyInfo:
    return GameLobbyInfo(
        gameId=db_game.id,
        gameName=db_game.name,
        minPlayers=db_game.min_players,
        maxPlayers=db_game.max_players,
        actualPlayers=db_game.num_players,
        ownerName=db_game.owner.name
    )