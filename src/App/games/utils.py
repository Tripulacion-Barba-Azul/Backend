from App.games.models import Game
from App.games.schemas import GameInfo, GameLobbyInfo, GameWaitingInfo
from App.players.utils import db_player_2_player_info


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

def db_game_2_game_wtg_info(db_game: Game) -> GameWaitingInfo:
    return GameWaitingInfo(
        gameId=db_game.id,
        gameName=db_game.name,
        minPlayers=db_game.min_players,
        maxPlayers=db_game.max_players,
        ownerId=db_game.owner_id,
        players=[db_player_2_player_info(db_player)
               for db_player in db_game.players]
    )