from fastapi import APIRouter, Depends, HTTPException, status

from App.card.schemas import CardGameInfo
from App.card.services import get_cards_by_player
from App.exceptions import NotPlayersTurnError, PlayerNotFoundError, WebsocketManagerNotFoundError
from App.games.services import GameService
from App.play.schemas import PlayCard, PlayCardInfo
from App.models.db import get_db
from App.play.services import RoundService
from App.players.schemas import PlayerGameInfo
from App.websockets import manager

play_router = APIRouter()

@play_router.post(path="/{game_id}/actions/play-card", status_code=200)
async def play_card(
    game_id: int,
    turn_info: PlayCard,
    db=Depends(get_db)):

    player_id = turn_info.playerId
    cards = turn_info.cards
    playerInGame = GameService(db).player_in_game(game_id, player_id)

    if cards == [] and playerInGame:
        try:
            
            game = RoundService(db).no_action(game_id, player_id)
            
            cards = []
            for player in game.players:
                for card in get_cards_by_player(player.id, db):
                    cards.append(CardGameInfo(
                        cardOwnerID=player.id,
                        cardID=card.id,
                        cardName=card.name
                    ))
                    
            players = []
            for player in game.players:
                players.append(PlayerGameInfo(
                    id=player.id,
                    name=player.name,
                    rol=str(player.rol)
                ))
                
            cardPlayInfo = PlayCardInfo(
                players=players,
                cards=cards
            )

            await manager.broadcast(game.id,cardPlayInfo.model_dump())
            
            return {}
            
        except PlayerNotFoundError as e:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
        except NotPlayersTurnError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"It's not the turn of player {player_id}",
            )

    elif not playerInGame:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The player is not in the game.",
        )
            
    elif cards != []:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playing cards is not implemented yet.",
        )
