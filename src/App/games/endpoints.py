from fastapi import APIRouter, Depends, HTTPException, status

from App.games.schemas import GameCreate, GameInfo
from App.games.services import GameService
from App.games.utils import db_game_2_game_info
from App.models.db import get_db
from App.players.schemas import PlayerCreate


games_router = APIRouter()


@games_router.post(path="", status_code=status.HTTP_201_CREATED)
async def create_game(
    player_info: PlayerCreate,
    game_info: GameCreate,
    db=Depends(get_db)
) -> GameInfo:
    try:
        created_game = GameService(db).create(
            player_dto=player_info.to_dto(),
            game_dto=game_info.to_dto()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return db_game_2_game_info(created_game)
