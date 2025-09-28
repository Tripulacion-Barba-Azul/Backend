from fastapi import APIRouter, Depends, HTTPException, status

from App.games.schemas import GameCreate, GameInfo, GameInfoPlayer, GameLobbyInfo, GameWaitingInfo
from App.games.services import GameService
from App.games.utils import db_game_2_game_info, db_game_2_game_info_player db_game_2_game_lobby_info, db_game_2_game_wtg_info

from App.models.db import get_db
from App.players.schemas import PlayerCreate
from App.websockets import get_manager
from App.exceptions import GameNotFoundError, GameFullError, GameAlreadyStartedError


games_router = APIRouter()

@games_router.get(path="", status_code=status.HTTP_200_OK)
async def get_games(db=Depends(get_db)) -> list[GameLobbyInfo]:
    return [db_game_2_game_lobby_info(game)
        for game in GameService(db).get_games()
    ]

@games_router.get(path="/{game_id}", status_code=status.HTTP_200_OK)
async def get_game(game_id: int, db=Depends(get_db)) -> GameWaitingInfo:
    db_game = GameService(db).get_by_id(game_id)
    if not db_game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {id} does not exist",
        )
    return db_game_2_game_wtg_info(db_game)
    
    


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
) -> GameInfoPlayer:
    try:
        joined_game, new_player = GameService(db).join(
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
    return db_game_2_game_info_player(joined_game, new_player)