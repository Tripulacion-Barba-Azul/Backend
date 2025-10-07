from fastapi import APIRouter, Depends, HTTPException, status

from App.card.schemas import CardGameInfo
from App.card.services import get_cards_by_player
from App.exceptions import NotPlayersTurnError, PlayerNotFoundError, WebsocketManagerNotFoundError
from App.games.services import GameService
from App.play.schemas import PlayCardInfo
from App.models.db import get_db
from App.play.services import RoundService
from App.players.schemas import PlayerGameInfo
from App.websockets import get_manager

play_router = APIRouter()

@play_router.post(path="/{game_id}/actions/play-card", status_code=200)
async def play_card(
    game_id: int,
    player_id: int,
    cards: list[int],
    db=Depends(get_db)):

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
                
            manager = get_manager(game_id)
            if manager:
                await manager.broadcast(cardPlayInfo.model_dump())
            
        except PlayerNotFoundError as e:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
        except NotPlayersTurnError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
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
