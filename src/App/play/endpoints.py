from fastapi import APIRouter, Depends, HTTPException, status


from App.exceptions import (
    InvalididDetectiveSet,
    NotCardInHand,
    NotPlayersTurnError,
    ObligatoryDiscardError,
    PlayerNotFoundError,
    DeckNotFoundError,
    PlayerHave6CardsError)

from App.games.enums import GameStatus
from App.games.schemas import GameEndInfo, PrivateUpdate, PublicUpdate
from App.games.services import GameService
from App.games.utils import db_game_2_game_detectives_win, db_game_2_game_public_info
from App.play.schemas import DrawCardInfo, PlayCard
from App.models.db import get_db

from App.play.services import PlayService
from App.players.models import Player

from App.players.utils import db_player_2_played_cards_played_info, db_player_2_player_private_info
from App.websockets import manager
from App.play.enums import ActionType
from App.sets.services import DetectiveSetService

play_router = APIRouter()

@play_router.post(path="/{game_id}/actions/play-card", status_code=200)
async def play_card(
    game_id: int,
    turn_info: PlayCard,
    db=Depends(get_db)):

    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )

    player_id = turn_info.playerId
    cards_id = turn_info.cards
    isPlayerInGame = GameService(db).player_in_game(game_id, player_id)

    if not isPlayerInGame:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The player is not in the game.",
        )

    player = db.query(Player).filter(Player.id == player_id).first()

    try:
        if len(cards_id) > 1:
            played_set = PlayService(db).play_set(player_id, cards_id)

            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
            event = DetectiveSetService(db).select_event_type(played_set.type).value
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message={"event": event}
            )

            playedCards = db_player_2_played_cards_played_info(player, played_set, cards_id, ActionType.SET)
            await manager.broadcast_except(
                game_id=game.id, 
                exclude_player_id=player.id,
                message=playedCards.model_dump()
            )

            return {"setId": played_set.id}
        
        elif cards_id == []:
                    
            game = PlayService(db).no_action(game_id, player_id)

            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
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
    except NotCardInHand as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="That card does not belong to the player.",
    )
    except InvalididDetectiveSet as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a valid detective set. Learn the rules little cheater.",
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
        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))

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
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )
    player_id = action.playerId
    isPlayerInGame = GameService(db).player_in_game(game_id, player_id)
    order = action.order

    if not isPlayerInGame:  
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found in game {game_id}",
        )
    
    player = db.query(Player).filter(Player.id == player_id).first()


    if action.deck == "regular":
        if order is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The order field is only for draft deck",
            )
        try:
            PlayService(db).draw_card_from_deck(game_id, player_id)

            if len(player.cards) == 6:
                PlayService(db).end_turn(game_id, player_id)

            gamePublicInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id, gamePublicInfo.model_dump())

            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )

            game = PlayService(db).end_game(game_id)
            if game.status == GameStatus.FINISHED:
                gameEndInfo = GameEndInfo(payload= db_game_2_game_detectives_win(game))
                await manager.broadcast(game.id, gameEndInfo.model_dump())
                return {"message": "The game has ended"}
        
        except NotPlayersTurnError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
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
    elif action.deck == "draft":
        if order not in [1, 2, 3]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The order field must be 1, 2 or 3",
            )
        try:
            
            PlayService(db).draw_card_from_draft(game_id, player_id, order)

            if len(player.cards) == 6:
                    PlayService(db).end_turn(game_id, player_id)
                
            gamePublicInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id, gamePublicInfo.model_dump())

            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )

            game = PlayService(db).end_game(game_id)
            if game.status == GameStatus.FINISHED:
                gameEndInfo = GameEndInfo(payload= db_game_2_game_detectives_win(game))
                await manager.broadcast(game.id, gameEndInfo.model_dump())
                return {"message": "The game has ended"}
            
        except NotPlayersTurnError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
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
            )