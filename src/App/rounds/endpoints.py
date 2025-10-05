from fastapi import APIRouter, Depends, HTTPException, status

from App.exceptions import NotPlayersTurnError, PlayerNotFoundError
from App.models.db import get_db
from App.rounds.services import RoundService

rounds_router = APIRouter()

@rounds_router.post(path="/{game_id}/actions/play-card", status_code=200)
async def play_card(
    game_id: int,
    cards: list[int], 
    player_id: int, 
    db=Depends(get_db)):
    
    if not cards:
        try:
            RoundService(db).no_action(game_id,player_id)
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
            
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playing cards is not implemented yet.",
        )
