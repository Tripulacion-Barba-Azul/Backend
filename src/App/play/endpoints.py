from fastapi import APIRouter, Depends, HTTPException, status

from App.card.utils import db_card_2_card_info
from App.exceptions import (
    GameNotFoundError,
    InSocialDisgraceException,
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
from App.games.schemas import GameEndInfo, NotifierRevealSecret, PrivateUpdate, PublicUpdate, SecretRevealedInfo, TopFiveDelayTheMurder, TopFiveLookIntoTheAshes
from App.games.services import GameService

from App.games.utils import db_game_2_game_detectives_lose, db_game_2_game_public_info
from App.play.schemas import (
    AndThenThereWasOneMoreInfo, 
    DelayTheMurderInfo, 
    DrawCardInfo, 
    HideSecretInfo, 
    LookIntoTheAshesInfo, 
    NotifierAndThenThereWasOneMore, 
    NotifierDelayTheMurder, 
    NotifierHideSecret, 
    NotifierLookIntoTheAshes, 
    NotifierRevealSecretForce, 
    NotifierSatterthwaiteWild, 
    NotifierStealSet, 
    PayloadAndThenThereWasOneMore, 
    PayloadDelayTheMurder, 
    PayloadHideSecret, 
    PayloadLookIntoTheAshes, 
    PlayCard, 
    RevealOwnSecretInfo, 
    RevealSecretInfo, 
    SelectAnyPlayerInfo, 
    StealSetInfo, 
    PayloadHideSecret, 
    PayloadLookIntoTheAshes, 
    PlayCard, 
    RevealOwnSecretInfo, 
    RevealSecretInfo, NotifierStealSet, StealSetInfo, SelectAnyPlayerInfo)

from App.models.db import get_db

from App.play.services import PlayService
from App.players.enums import TurnAction
from App.players.models import Player

from App.players.utils import db_player_2_discarded_cards_info, db_player_2_played_card_info, db_player_2_played_cards_played_info, db_player_2_player_private_info, db_player_2_reveal_secret_force, db_player_2_satterthquin_info, db_player_cards_off_the_tables_info, turn_action_enum_2_str


from App.websockets import manager
from App.play.enums import ActionType
from App.sets.services import DetectiveSetService
from App.games.models import Game

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
            event = DetectiveSetService(db).select_event_type(game, played_set.type)
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message={"event": turn_action_enum_2_str(event)}
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
                topFiveCardsInfo = TopFiveLookIntoTheAshes(payload = [db_card_2_card_info(c) for c in top_cards])
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=player.id,
                    message=topFiveCardsInfo.model_dump()
                    )
            elif player.turn_action == TurnAction.DELAY_THE_MURDERER:
                top_cards = PlayService(db).get_top_five_discarded_cards(game.id)
                topFiveCardsInfo = TopFiveDelayTheMurder(payload = [db_card_2_card_info(c) for c in top_cards])
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=player.id,
                    message=topFiveCardsInfo.model_dump()
                    )
            elif player.turn_action == TurnAction.EARLY_TRAIN_TO_PADDINGTON:
                PlayService(db).early_train_to_paddington(game, player)
                gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
                await manager.broadcast(game.id,gamePublictInfo.model_dump())
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
            else:
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=player.id,
                    message={"event": turn_action_enum_2_str(event)}
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
        discarded_cards = PlayService(db).discard(game, turn_info.playerId, turn_info.cards)
        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))

            await manager.send_to_player(
                game_id=game.id, 
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
        
        discardEventinfo = db_player_2_discarded_cards_info(
            player_id=turn_info.playerId,
            discarded_cards=discarded_cards
        )
        await manager.broadcast_except(game.id,turn_info.playerId,discardEventinfo.model_dump())

        
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
    except InSocialDisgraceException as e:
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

            if player.in_social_disgrace or len(player.cards) == 6:
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

            if player.in_social_disgrace or len(player.cards) == 6:
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

@play_router.post(path="/{game_id}/actions/select-any-player", status_code=200)
async def select_any_player(
        game_id: int,
        select_player_info: SelectAnyPlayerInfo,
        db=Depends(get_db)
        ):
    player_id = select_player_info.playerId
    selected_player_id = select_player_info.selectedPlayerId
    try:
        game, player, selected_player, event, countNotSoFast = PlayService(db).select_any_player(
            game_id,
            player_id,
            selected_player_id
        )
        
        if event == TurnAction.CARDS_OFF_THE_TABLE:

            gamePublicInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id, gamePublicInfo.model_dump())

            for p in game.players:
                playerPrivateInfo = PrivateUpdate(payload=db_player_2_player_private_info(p))

                await manager.send_to_player(
                    game_id=game.id,
                    player_id=p.id,
                    message=playerPrivateInfo.model_dump()
                )
            if not countNotSoFast:
                countNotSoFast = 0
            cardsOffTheTableInfo = db_player_cards_off_the_tables_info(player, selected_player, countNotSoFast)
            await manager.broadcast(game.id, cardsOffTheTableInfo.model_dump())

        elif event in [TurnAction.SELECT_ANY_PLAYER, TurnAction.SATTERWAITEWILD]:
            await manager.send_to_player(
                game_id=game.id,
                player_id=selected_player.id,
                message={"event": turn_action_enum_2_str(selected_player.turn_action)}
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
    

@play_router.post(path="/{game_id}/actions/reveal-own-secret", status_code=200)
async def reveal_own_secret(
    game_id: int,
    turn_info: RevealOwnSecretInfo,
    db=Depends(get_db)
):
    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )

    player_id = turn_info.playerId
    secret_id = turn_info.secretId

    try:
        event, player, secret, selected_player = PlayService(db).select_own_secret(
            game,
            player_id,
            secret_id
        )

        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
            
        for p in game.players:
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(p))

            await manager.send_to_player(
                game_id=game.id, 
                player_id=p.id,
                message=playerPrivateInfo.model_dump()
            )

        if event == TurnAction.REVEAL_OWN_SECRET:
            eventInfo = NotifierRevealSecretForce(
                payload=db_player_2_reveal_secret_force(player,secret,selected_player)
            )
            await manager.broadcast(game.id, eventInfo.model_dump())
        elif event == TurnAction.GIVE_SECRET_AWAY:
            eventInfo = NotifierSatterthwaiteWild(
                payload=db_player_2_satterthquin_info(player,secret,selected_player)
            )
            await manager.broadcast(game.id, eventInfo.model_dump())

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

@play_router.post(path="/{game_id}/actions/delay-the-murderers-escape", status_code=200)
async def delay_the_murderers_escape(
    game_id: int,
    turn_info: DelayTheMurderInfo,
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
        PlayService(db).delay_the_murder_effect(
            game=game,
            player_id=player_id,
            cards=turn_info.cards,
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

        notifierDelayTheMurder = NotifierDelayTheMurder(
            payload=PayloadDelayTheMurder(
                playerId=player_id
            )
        )

        await manager.broadcast(game.id, notifierDelayTheMurder.model_dump())
  
        return {"Delay the Murderers Escape success"}
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