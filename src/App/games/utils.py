
from App.card.utils import db_card_2_card_info
from App.games.models import Game

from App.games.schemas import GameInfo, GameInfoPlayer, GameLobbyInfo, GamePublicInfo, GameWaitingInfo
from App.players.enums import PlayerRole
from App.players.models import Player
from App.players.schemas import PlayerWinInfo
from App.players.utils import db_player_2_player_info, db_player_2_player_public_info


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


def db_game_2_game_public_info(db_game: Game) -> GamePublicInfo:

    return GamePublicInfo(
        actionStatus=db_game.action_status.value,
        gameStatus=db_game.status.value,
        regularDeckCount=len(db_game.reposition_deck.cards),
        discardPileTop=db_card_2_card_info(db_game.discard_deck.cards[0]),
        draftCards= [], #falta implementar draft cards
        discardPileCount= len(db_game.discard_deck.cards),
        players=[db_player_2_player_public_info(player) for player in db_game.players]
    )
    
def db_game_2_game_detectives_win(db_game: Game) -> list[PlayerWinInfo]:
    return [PlayerWinInfo(
                name=player.name,
                role=player.role.value
            ) for player in db_game.players if player.role == PlayerRole.DETECTIVE]