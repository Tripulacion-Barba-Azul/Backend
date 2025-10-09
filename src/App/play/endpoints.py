from fastapi import APIRouter, Depends, HTTPException, status

from App.card.schemas import CardGameInfo
<<<<<<< HEAD
from App.exceptions import (
    DeckNotFoundError,
    NotPlayersTurnError,
    PlayerHave6CardsError,
    PlayerNotFoundError)
=======
from App.exceptions import NotPlayersTurnError, ObligatoryDiscardError, PlayerNotFoundError
>>>>>>> develop
from App.games.services import GameService
from App.games.utils import db_game_2_game_public_info
from App.play.schemas import DrawCardInfo, PlayCard, PlayCardInfo
from App.models.db import get_db

from App.play.services import PlayService
from App.players.models import Player
from App.players.schemas import PlayerGameInfo
from App.players.services import PlayerService
from App.players.utils import db_player_2_player_private_info
from App.websockets import manager

play_router = APIRouter()

@play_router.post(path="/{game_id}/actions/play-card", status_code=200)
async def play_card(
    game_id: int,
    turn_info: PlayCard,
    db=Depends(get_db)):

    game = GameService(db).get_by_id(game_id)
    player_id = turn_info.playerId
    cards_id = turn_info.cards
    isPlayerInGame = GameService(db).player_in_game(game_id, player_id)

    player = db.query(Player).filter(Player.id == player_id).first()

    if cards_id == [] and isPlayerInGame:
        try:
            
            game = PlayService(db).no_action(game_id, player_id)
            
            gamePublictInfo = db_game_2_game_public_info(game)
            await manager.broadcast(game.id,gamePublictInfo.model_dump())
            playerPrivateInfo = db_player_2_player_private_info(player)
            await manager.send_to_player(
                game_id=game.id, 
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
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

    elif not isPlayerInGame:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The player is not in the game.",
        )
            
    elif cards_id != []:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playing cards is not implemented yet.",
        )


@play_router.post(path="/{game_id}/actions/discard", status_code=200)
async def discard_cards(
    game_id: int,
    turn_info: PlayCard,
    db=Depends(get_db)):

    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )

    try:
        PlayService(db).discard(game, turn_info.playerId, turn_info.cards)
        gamePublictInfo = db_game_2_game_public_info(game)
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        for player in game.players:
            playerPrivateInfo = db_player_2_player_private_info(player)

            await manager.send_to_player(
                game_id=game.id, 
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
    except PlayerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except NotPlayersTurnError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"It's not the turn of player {turn_info.playerId}",
        )
    except ObligatoryDiscardError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )



@play_router.post(path="/{game_id}/actions/draw-card", status_code=200)
async def draw_card(
    game_id: int,
    action: DrawCardInfo,
    db=Depends(get_db)
    ):
    game = GameService(db).get_by_id(game_id)
    player_id = action.playerId
    isPlayerInGame = GameService(db).player_in_game(game_id, player_id) 
 
    if not isPlayerInGame:  
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PlayerNotFoundError,
        )
    
    player = db.query(Player).filter(Player.id == player_id).first()

    
    
    try:
        card = PlayService(db).draw_card_from_deck(game_id, player_id)
        gamePublictInfo = db_game_2_game_public_info(game)

        await manager.broadcast(game.id,gamePublictInfo.model_dump())

        playerPrivateInfo = db_player_2_player_private_info(player)

        await manager.send_to_player(
            game_id=game.id, 
            player_id=player.id,
            message=playerPrivateInfo.model_dump()
        )
        cardInfo = CardGameInfo(
            cardOwnerID=player.id,
            cardID = card.id,
            cardName = card.name
        )
        return cardInfo.model_dump()
    
    except NotPlayersTurnError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
    except PlayerHave6CardsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
    except PlayerNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
    except DeckNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )