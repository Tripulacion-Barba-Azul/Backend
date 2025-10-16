from fastapi import APIRouter, Depends, HTTPException, status

from App.card.utils import db_card_2_card_info
from App.exceptions import (
    GameNotFoundError,
    InvalididDetectiveSet,
    NotCardInHand,
    NotPlayersTurnError,
    ObligatoryDiscardError,
    PlayerNotFoundError,
    DeckNotFoundError,
    PlayerHave6CardsError,
    SecretAlreadyRevealedError,
    SecretNotFoundError,
    SecretNotRevealed)

from App.games.enums import GameStatus
from App.games.schemas import GameEndInfo, NotifierRevealSecret, PrivateUpdate, PublicUpdate, SecretRevealedInfo, TopFiveInfo
from App.games.services import GameService

from App.games.utils import db_game_2_game_detectives_lose, db_game_2_game_public_info
from App.play.schemas import AndThenThereWasOneMoreInfo, DrawCardInfo, HideSecretInfo, LookIntoTheAshesInfo, NotifierAndThenThereWasOneMore, NotifierHideSecret, NotifierLookIntoTheAshes, PayloadAndThenThereWasOneMore, PayloadHideSecret, PayloadLookIntoTheAshes, PlayCard, RevealSecretInfo, NotifierStealSet, StealSetInfo, SelectAnyPlayerInfo

from App.models.db import get_db

from App.play.services import PlayService
from App.players.enums import TurnAction
from App.players.models import Player

from App.players.utils import db_player_2_played_card_info, db_player_2_played_cards_played_info, db_player_2_player_private_info, db_player_cards_off_the_tables_info


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
            played_set = PlayService(db).play_set(game, player_id, cards_id)

            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
            event = DetectiveSetService(db).select_event_type(game, played_set.type).value
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
        
        elif len(cards_id) == 1:
            card_id = cards_id[0]
            card, event = PlayService(db).play_card(game, player_id, card_id)

            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )

            if player.turn_action == TurnAction.LOOK_INTO_THE_ASHES:
                top_cards = PlayService(db).get_top_five_discarded_cards(game.id)
                topFiveCardsInfo = TopFiveInfo(payload = [db_card_2_card_info(c) for c in top_cards])
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=player.id,
                    message=topFiveCardsInfo.model_dump()
                    )
            else:
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=player.id,
                    message={"event": event.value}
                )


            playedCard = db_player_2_played_card_info(player, card, ActionType.EVENT)
            await manager.broadcast_except(
                game_id=game.id, 
                exclude_player_id=player.id,
                message=playedCard.model_dump()
            )

            return {"playedCardName": card.name}
    
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
                gameEndInfo = GameEndInfo(payload= db_game_2_game_detectives_lose(game))
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
                gameEndInfo = GameEndInfo(payload= db_game_2_game_detectives_lose(game))
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

@play_router.post(path="/{game_id}/actions/steal-set", status_code=200)
async def steal_set(
    game_id:int,
    turn_info: StealSetInfo,
    db=Depends(get_db)
    ):

    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )
    
    player_id = turn_info.playerId
    stolen_played_id = turn_info.stolenPlayerId
    set_id = turn_info.setId
    try:
        
        dset = PlayService(db).steal_set(player_id, stolen_played_id, set_id)

        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))

            await manager.send_to_player(
                game_id=game.id, 
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
        
        notifierStealSet = NotifierStealSet(
            payload=StealSetInfo(
                playerId=player_id,
                stolenPlayerId= stolen_played_id,
                setId = dset.id
            )
        )
        await manager.broadcast(game.id, notifierStealSet.model_dump())

        return {"stolenSetId": dset.id}

    except PlayerNotFoundError as e:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(e),
    )
    except InvalididDetectiveSet as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Detective set {set_id} not found",
    )
  
@play_router.post(path="/{game_id}/actions/reveal-secret", status_code=200)
async def endpoint_reveal_secret(
    game_id: int,
    action: RevealSecretInfo,
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
    secret_id = action.secretId
    revealed_player_id = action.revealedPlayerId

    if not isPlayerInGame:  
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found in game {game_id}",
        )
    
    isPlayerInGame = GameService(db).player_in_game(game_id, revealed_player_id)

    if not isPlayerInGame:  
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {revealed_player_id} not found in game {game_id}",
        )

    try:
        PlayService(db).reveal_secret_service(player_id, secret_id, revealed_player_id)

        gamePublicInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id, gamePublicInfo.model_dump())


        notifierRevealSecret = NotifierRevealSecret(
            payload=SecretRevealedInfo(
                playerId=player_id,
                secretId=secret_id,
                selectedPlayerId=revealed_player_id
            )
        )
        await manager.broadcast(game.id, notifierRevealSecret.model_dump())

        return {"message": "Secret revealed successfully"}

        
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
    except SecretNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SecretAlreadyRevealedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@play_router.post(path="/{game_id}/actions/select_any_player", status_code=200)
async def select_any_player(
        game_id: int,
        select_player_info: SelectAnyPlayerInfo,
        db=Depends(get_db)
        ):
    
    try:
        game, player, selected_player = PlayService(db).select_any_player(
            game_id,
            select_player_info.playerId,
            select_player_info.selectedPlayerId
        )
        
        event = player.turn_action
        if event == TurnAction.CARDS_OFF_THE_TABLE:
            countNotSoFast = PlayService(db).cards_off_the_tables(game, player, selected_player)

            cardsOffTheTableInfo = db_player_cards_off_the_tables_info(player, selected_player, countNotSoFast)
            await manager.broadcast(game.id, cardsOffTheTableInfo.model_dump())

        """ elif event == TurnAction.SELECT_ANY_PLAYER_SETS:
            await manager.broadcast(game.id, event_type = "select_any_player_sets") """
            
        gamePublicInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id, gamePublicInfo.model_dump())

        playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
        await manager.send_to_player(
            game_id=game.id,
            player_id=player.id,
            message=playerPrivateInfo.model_dump()
        )
        
    except (GameNotFoundError, PlayerNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except NotPlayersTurnError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    
    return {"message": "Player selected successfully"}

@play_router.post(path="/{game_id}/actions/hide-secret", status_code=200)
async def hide_secret(
    game_id:int,
    turn_info: HideSecretInfo,
    db=Depends(get_db)
    ):

    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )
    
    player_id = turn_info.playerId
    affected_player_id = turn_info.hiddenPlayerId
    secret_id = turn_info.secretId
    try:
        
        secret = PlayService(db).hide_secret(player_id, secret_id, affected_player_id)

        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))

            await manager.send_to_player(
                game_id=game.id, 
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
        
        notifierStealSet = NotifierHideSecret(
            payload=PayloadHideSecret(
                playerId=player_id,
                secretId= secret.id,
                selectedPlayerId=affected_player_id
            )
        )
        
        await manager.broadcast(game.id, notifierStealSet.model_dump())

        return {"hiddenSecretId": secret.id}

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
    except SecretNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SecretNotRevealed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    

@play_router.post(path="/{game_id}/actions/and-then-there-was-one-more", status_code=200)
async def and_then_there_was_one_more(
    game_id:int,
    turn_info: AndThenThereWasOneMoreInfo,
    db=Depends(get_db)
    ):

    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )
    
    player_id = turn_info.playerId
    stolen_player_id = turn_info.stolenPlayerId
    selected_player_id = turn_info.selectedPlayerId
    secret_id = turn_info.secretId
    try:
        secret = PlayService(db).and_then_there_was_one_more_effect(
            player_id=player_id,
            secret_id=secret_id,
            stolen_player_id=stolen_player_id,
            selected_player_id=selected_player_id
        )

        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))

            await manager.send_to_player(
                game_id=game.id, 
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
        
        notifierStealSet = NotifierAndThenThereWasOneMore(
            payload=PayloadAndThenThereWasOneMore(
                playerId=player_id,
                secretId=secret.id,
                secretName=secret.name,
                stolenPlayerId=stolen_player_id,
                giftedPlayerId=selected_player_id
            )
        )
        
        await manager.broadcast(game.id, notifierStealSet.model_dump())

        return {"hiddenSecretId": secret.id}

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
    except SecretNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SecretNotRevealed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
@play_router.post(path="/{game_id}/actions/look-into-the-ashes", status_code=200)
async def look_into_the_ashes(
    game_id: int,
    turn_info: LookIntoTheAshesInfo,
    db=Depends(get_db)
):
    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )

    player_id = turn_info.playerId
    try:
        card = PlayService(db).look_into_the_ashes_effect(
            game=game,
            player_id=player_id,
            card_id=turn_info.cardId,
        )

        gamePublictInfo = PublicUpdate(payload=db_game_2_game_public_info(game))
        await manager.broadcast(game.id, gamePublictInfo.model_dump())

        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload=db_player_2_player_private_info(player))

            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )

        notifierLookIntoTheAshes = NotifierLookIntoTheAshes(
            payload=PayloadLookIntoTheAshes(
                playerId=player_id
            )
        )

        await manager.broadcast(game.id, notifierLookIntoTheAshes.model_dump())

        return {"takenCardId": card.id}

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
    except SecretNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SecretNotRevealed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )