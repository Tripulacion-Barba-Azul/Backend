from fastapi import APIRouter, Depends, HTTPException, status

from App.games.schemas import GameCreate, GameInfo
from App.games.services import GameService
from App.games.utils import db_game_2_game_info, db_game_2_game_info_player
from App.models.db import get_db
from App.players.schemas import PlayerCreate
from App.websockets import get_manager
from App.exceptions import GameNotFoundError, GameFullError, GameAlreadyStartedError


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

@games_router.post(path="/{game_id}/join", status_code=status.HTTP_200_OK)
async def join_game(
    game_id: int,
    player_info: PlayerCreate,
    db=Depends(get_db)
) -> GameInfo:
    try:
        joined_game = GameService(db).join(
            game_id=game_id,
            player_dto=player_info.to_dto()
        )
    except GameNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (GameFullError, GameAlreadyStartedError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    manager = get_manager(game_id)
    if not manager:
        raise HTTPException(status_code=400, detail="No WebSocket manager for this game")
    await manager.broadcast({"event": "player_joined", "player": player_info.playerName})
    return db_game_2_game_info_player(joined_game, player_info)