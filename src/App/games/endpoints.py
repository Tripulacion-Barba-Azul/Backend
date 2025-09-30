from fastapi import APIRouter, Depends, HTTPException, status

from App.card.schemas import CardGameInfo
from App.card.services import get_cards_by_player
from App.games.models import Game
from App.games.schemas import GameCreate, GameInfo, GameInfoPlayer, GameLobbyInfo, GameStartInfo, GameWaitingInfo
from App.games.services import GameService
from App.games.utils import (
    db_game_2_game_info,
    db_game_2_game_info_player,
    db_game_2_game_lobby_info,
    db_game_2_game_wtg_info
)
from App.models.db import get_db
from App.players.schemas import PlayerCreate, PlayerGameInfo
from App.secret.schemas import SecretGameInfo
from App.secret.services import get_secrets_by_player
from App.websockets import get_manager, create_manager
from App.exceptions import (
    GameNotFoundError,
    GameFullError,
    GameAlreadyStartedError,
    NotEnoughPlayers,
    NotTheOwnerOfTheGame,
    WebsocketManagerNotFoundError
)

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

        create_manager(created_game.id)
        manager= get_manager(created_game.id)
        if not manager:
            raise WebsocketManagerNotFoundError("No WebSocket manager for this game")
        await manager.broadcast({"event": "player_joined", "player": player_info.playerName})
        
    except WebsocketManagerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
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

        manager = get_manager(game_id)
        await manager.broadcast({"event": "player_joined", "player": player_info.playerName}) # type: ignore

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

    return db_game_2_game_info_player(joined_game, new_player)


@games_router.post(path="/{game_id}/start", status_code=status.HTTP_200_OK)
async def start_game(
    game_id: int,
    owner_id: int,
    db=Depends(get_db)
) -> GameInfo:
    try:
        db_game = GameService(db).start(game_id, owner_id)

        player_turn_id = GameService(db).select_player_turn(db_game.id)
        players = []
        for player in db_game.players:
            players.append(PlayerGameInfo(
                id=player.id,
                name=player.name,
                rol=str(player.rol)
            ))
        
        number_deck_cards = len(db_game.reposition_deck.cards)

        cards = []
        for player in db_game.players:
            for card in get_cards_by_player(player.id, db):
                cards.append(CardGameInfo(
                    cardOwnerID=player.id,
                    cardID=card.id,
                    cardName=card.name
                ))
        
        secrets = []
        for player in db_game.players:
            for secret in get_secrets_by_player(player.id, db):
                secrets.append(SecretGameInfo(
                    secretOwnerID=player.id,
                    secretName=secret.name,
                    revealed=secret.revealed
                ))

        gameStartInfo = GameStartInfo(
            playerTurnId=player_turn_id,
            numberOfRemainingCards=number_deck_cards,
            players=players,
            cards=cards,
            secrets=secrets
        )
        manager = get_manager(db_game.id)
        await manager.broadcast(gameStartInfo.model_dump()) # type: ignore

        return db_game_2_game_info(db_game)
    except GameNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except NotTheOwnerOfTheGame as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except NotEnoughPlayers as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except GameAlreadyStartedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
