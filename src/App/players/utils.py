from App.players.models import Player
from App.players.schemas import PlayerInfo


def db_player_2_player_info(db_player: Player) -> PlayerInfo:
    return PlayerInfo(
        playerId=db_player.id,
        playerName=db_player.name,
        birthDate=db_player.birthday
    )