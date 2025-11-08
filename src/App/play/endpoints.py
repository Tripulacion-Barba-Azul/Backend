import asyncio
from anyio import NoEventLoopError
from fastapi import APIRouter, Depends, HTTPException, status

from App.card.utils import db_card_2_card_info
from App.exceptions import (
    GameIsBlocked,
    GameNotFoundError,
    InSocialDisgraceException,
    InvalididDetectiveSet,
    NotCardInHand,
    NotPlayableCard,
    NotPlayersTurnError,
    ObligatoryDiscardError,
    PlayerNotFoundError,
    DeckNotFoundError,
    PlayerHave6CardsError,
    SecretAlreadyRevealedError,
    SecretNotFoundError,
    SecretNotRevealed)

from App.games.enums import ActionStatus, GameStatus
from App.games.schemas import GameEndInfo, NotifierRevealSecret, PrivateUpdate, PublicUpdate, SecretRevealedInfo, TopFiveDelayTheMurder, TopFiveLookIntoTheAshes
from App.games.services import GameService

from App.games.utils import db_game_2_game_end_info, db_game_2_game_public_info
from App.play.schemas import (
    AddDetectiveInfo,
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
    PlayNSF, 
    RevealOwnSecretInfo, 
    RevealSecretInfo, 
    SelectAnyPlayerInfo, 
    StealSetInfo, 
    PayloadHideSecret, 
    PayloadLookIntoTheAshes, 
    PlayCard, 
    RevealOwnSecretInfo, 
    RevealSecretInfo, NotifierStealSet, StealSetInfo, SelectAnyPlayerInfo,
    TimeInfo)

from App.models.db import get_db

from App.play.services import PlayService
from App.players.enums import TurnAction
from App.players.models import Player

from App.players.utils import db_player_2_discarded_cards_info, db_player_2_played_card_info, db_player_2_played_cards_played_info, db_player_2_played_detective_info, db_player_2_player_private_info, db_player_2_reveal_secret_force, db_player_2_satterthquin_info, db_player_cards_off_the_tables_info, turn_action_enum_2_str


from App.websockets import manager
from App.play.enums import ActionType
from App.sets.services import DetectiveSetService
from App.games.models import Game
from App.events.models import Event
from App.events.services import EventManager
from App.sets.enums import DetectiveSetType
from App.events.enums import EventType
from App.card.services import CardService

play_router = APIRouter()

# Diccionario global: game_id -> asyncio.Task
active_timers: dict[int, asyncio.Task] = {}

# Duración del timer (en segundos)
TIMER_DURATION = 11

async def start_timer(game_id: int, db):
    """Crea un timer que envía updates cada 1s y resuelve al finalizar."""
    time_left = TIMER_DURATION
    print(f"[TIMER] Started for game {game_id} ({time_left}s)")
    
    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )
    
    try:
        game = GameService(db).get_by_id(game_id)
        while time_left >= 0:

            # Enviar info del tiempo restante
            time_info = TimeInfo(payload={
                "eventTime": TIMER_DURATION,
                "timeLeft": time_left
            })
            await manager.broadcast(game_id, time_info.model_dump())

            # Esperar 1 segundo
            await asyncio.sleep(1)
            time_left -= 1
        
        # Se acabó el tiempo: resolver evento
        print(f"[TIMER] Resolving game {game_id} after timeout.")
        await resolve_event(game_id, db)
        
    except asyncio.CancelledError:
        # Si el timer fue reiniciado o cancelado
        print(f"[TIMER] Cancelled for game {game_id}")
        # (opcional) enviar broadcast de cancelación
        cancel_info = {"event": "timer_cancelled"}
        await manager.broadcast(game_id, cancel_info)
        raise

def reset_timer(game_id: int, db):
    """Cancela el timer previo (si existe) y crea uno nuevo."""
    # Cancelar el timer previo
    task = active_timers.get(game_id)
    if task and not task.done():
        task.cancel()
        print(f"[TIMER] Cancelled old timer for game {game_id}")

    # Crear nuevo timer asíncrono
    task = asyncio.create_task(start_timer(game_id, db))
    active_timers[game_id] = task
    print(f"[TIMER] Started new timer for game {game_id}")

async def resolve_event(game_id:int, db):
    
    game = GameService(db).get_by_id(game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )
    event: Event | None = EventManager(db).resolve(game_id)

    # Broadcast final con el resultado
    game = GameService(db).get_by_id(game_id)
    if game is None:
        return
    if event is None:

        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        for p in game.players:
                playerPrivateInfo = PrivateUpdate(payload=db_player_2_player_private_info(p))
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=p.id,
                    message=playerPrivateInfo.model_dump()
                )

    if event is not None and event.type == EventType.PLAY_SET:
        game = event.game
        player = event.main_player
        dset = event.dset

        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        turn_action = DetectiveSetService(db).select_event_type(game, dset.type)
        await manager.send_to_player(
            game_id=game.id,
            player_id=player.id,
            message={"event": turn_action_enum_2_str(turn_action)}
        )
    if event is not None and event.type == EventType.PLAY_CARD:
        game = event.game
        player = event.main_player
        card = event.played_card

        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
        await manager.send_to_player(
            game_id=game.id,
            player_id=player.id,
            message=playerPrivateInfo.model_dump()
        )

        if card.name == "Look in to the Ashes":
            top_cards = PlayService(db).get_top_five_discarded_cards(player,game.id)
            topFiveCardsInfo = TopFiveLookIntoTheAshes(payload = [db_card_2_card_info(c) for c in top_cards])
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=topFiveCardsInfo.model_dump()
                )
        elif card.name == "Delay the Muderer's Escape":
            top_cards = PlayService(db).get_top_five_discarded_cards(player, game.id)
            topFiveCardsInfo = TopFiveDelayTheMurder(payload = [db_card_2_card_info(c) for c in top_cards])
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=topFiveCardsInfo.model_dump()
                )
        elif card.name == "Early Train to Paddington":
            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
                )
            
            if game.status == GameStatus.FINISHED:
                gameEndInfo = GameEndInfo(payload= db_game_2_game_end_info(game))
                await manager.broadcast(game.id, gameEndInfo.model_dump())
                return {"message": "The game has ended"}
        else:
            eventType = CardService(db).select_event_type(game, player, card)
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message={"event": turn_action_enum_2_str(eventType)}
            )
    if event is not None and event.type == EventType.PLAY_DETECTIVE:
        game = event.game
        player = event.selected_player
        dset = event.dset

        
        gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
        await manager.send_to_player(
            game_id=game.id,
            player_id=player.id,
            message=playerPrivateInfo.model_dump()
        )

        turn_action = player.turn_action
        await manager.send_to_player(
            game_id=game.id,
            player_id=player.id,
            message={"event": turn_action_enum_2_str(turn_action)}
        )
 
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
        # PLAYED A DETECTIVE SET
        if len(cards_id) > 1:

            # DETECTIVE SET IS PLAYED
            played_set = PlayService(db).play_set(game, player_id, cards_id)

            # SEND NEW GAME' STATE INFO
            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())

            playedCards = db_player_2_played_cards_played_info(player, played_set, cards_id, ActionType.SET)
            await manager.broadcast_except(
                game_id=game.id,
                exclude_player_id=player.id,
                message=playedCards.model_dump()
            )

            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )

            # TIME TO PLAY NSF
            if game.action_status is ActionStatus.UNBLOCKED:
                reset_timer(game_id, db)
            else:
            # RESOLVE NOT CANCELABLE EVENTS  
                EventManager(db).resolve(game.id)
                event = DetectiveSetService(db).select_event_type(game, played_set.type)
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=player.id,
                    message={"event": turn_action_enum_2_str(event)}
                )       

            return {"setId": played_set.id}
        
        # PLAYED AN EVENT CARD
        elif len(cards_id) == 1:

            # EVENT CARD IS PLAYED
            card_id = cards_id[0]
            card, event = PlayService(db).play_card(game, player_id, card_id)

            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())

            playedCard = db_player_2_played_card_info(player, card, ActionType.EVENT)
            await manager.broadcast_except(
                game_id=game.id, 
                exclude_player_id=player.id,
                message=playedCard.model_dump()
            )
            
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )

            # TIME TO PLAY NSF
            if game.action_status is ActionStatus.UNBLOCKED:
                reset_timer(game_id, db)
            else:
            # RESOLVE NOT CANCELABLE EVENTS  
                EventManager(db).resolve(game.id)
                await manager.send_to_player(
                    game_id=game.id,
                    player_id=player.id,
                    message={"event": turn_action_enum_2_str(event)}
                )

            # BROADCAST INFO
            # if game.status == GameStatus.FINISHED:
            #     gameEndInfo = GameEndInfo(payload= db_game_2_game_end_info(game))
            #     await manager.broadcast(game.id, gameEndInfo.model_dump())
            #     return {"message": "The game has ended"}
            # else:
            #     await manager.send_to_player(
            #         game_id=game.id,
            #         player_id=player.id,
            #         message={"event": turn_action_enum_2_str(event)}
            #     )

            playedCard = db_player_2_played_card_info(player, card, ActionType.EVENT)
            await manager.broadcast_except(
                game_id=game.id, 
                exclude_player_id=player.id,
                message=playedCard.model_dump()
            )

            return {"playedCardName": card.name}

        # SKIP TURN
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
    except NotPlayableCard as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Card",
    )

@play_router.post(path="/{game_id}/actions/play-nsf", status_code=200)
async def play_nsf(
    game_id: int,
    turn_info: PlayNSF,
    db=Depends(get_db)):

    game = GameService(db).get_by_id(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )

    player_id = turn_info.playerId
    card_id = turn_info.cardId
    isPlayerInGame = GameService(db).player_in_game(game_id, player_id)

    if not isPlayerInGame:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The player is not in the game.",
        )

    player = db.query(Player).filter(Player.id == player_id).first()

    try:
        # Add NSF Event and Block the game
        is_played = PlayService(db).play_nsf(game, player, card_id)

        if is_played:
            card = is_played[1]
            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())

            playedCards = db_player_2_played_card_info(player, card, ActionType.EVENT)
            await manager.broadcast_except(
                game_id=game.id,
                exclude_player_id=player.id,
                message=playedCards.model_dump()
            )
            
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
            # Stop timer
            task = active_timers.get(game_id)
            if task and not task.done():
                task.cancel()
        elif all(player.turn_action == TurnAction.NO_ACTION for player in game.players):
            task = active_timers.get(game_id)
            if task and not task.done():
                task.cancel()
            time_info = TimeInfo(payload={
                "eventTime": TIMER_DURATION,
                "timeLeft": TIMER_DURATION
            })
            await manager.broadcast(game_id, time_info.model_dump())
            task = asyncio.create_task(resolve_event(game_id, db))
            return
        
        
        # Broadcast
        gamePublictInfo = PublicUpdate(payload=db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        for p in game.players:
            playerPrivateInfo = PrivateUpdate(payload=db_player_2_player_private_info(p))

            await manager.send_to_player(
                game_id=game.id,
                player_id=p.id,
                message=playerPrivateInfo.model_dump()
            )

        print("AWAIT")
        await asyncio.sleep(1)
        # Unblock de game and restart timer
        print("UNBLOCK GAME")
        gamePublictInfo = PublicUpdate(payload=db_game_2_game_public_info(game))
        await manager.broadcast(game.id,gamePublictInfo.model_dump())
        
        for p in game.players:
            playerPrivateInfo = PrivateUpdate(payload=db_player_2_player_private_info(p))

            await manager.send_to_player(
                game_id=game.id,
                player_id=p.id,
                message=playerPrivateInfo.model_dump()
            )
        if is_played:
            reset_timer(game_id, db)
            PlayService(db).restart_nsf(game)
            gamePublictInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id,gamePublictInfo.model_dump())

    except GameIsBlocked as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game is Blocked",
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
    except NotPlayableCard as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card is not a Not So Fast",
    )

    return {"message": "Not So Fast played successfully"}

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

        
        if game.status == GameStatus.FINISHED:
            gameEndInfo = GameEndInfo(payload= db_game_2_game_end_info(game))
            await manager.broadcast(game.id, gameEndInfo.model_dump())
            return {"message": "The game has ended"}
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
                gameEndInfo = GameEndInfo(payload= db_game_2_game_end_info(game))
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
                gameEndInfo = GameEndInfo(payload= db_game_2_game_end_info(game))
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
        PlayService(db).reveal_secret_service(game, player_id, secret_id, revealed_player_id)

        gamePublicInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
        await manager.broadcast(game.id, gamePublicInfo.model_dump())

        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload = db_player_2_player_private_info(player))
            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )

        notifierRevealSecret = NotifierRevealSecret(
            payload=SecretRevealedInfo(
                playerId=player_id,
                secretId=secret_id,
                selectedPlayerId=revealed_player_id
            )
        )
        await manager.broadcast(game.id, notifierRevealSecret.model_dump())
        game = PlayService(db).end_game(game_id)
        if game.status == GameStatus.FINISHED:
            gameEndInfo = GameEndInfo(payload= db_game_2_game_end_info(game))
            await manager.broadcast(game.id, gameEndInfo.model_dump())
            return {"message": "The game has ended"}

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
            
        elif event == TurnAction.NO_ACTION:

            gamePublicInfo = PublicUpdate(payload = db_game_2_game_public_info(game))
            await manager.broadcast(game.id, gamePublicInfo.model_dump())

            for p in game.players:
                playerPrivateInfo = PrivateUpdate(payload=db_player_2_player_private_info(p))

                await manager.send_to_player(
                    game_id=game.id,
                    player_id=p.id,
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
        
        secret = PlayService(db).hide_secret(game, player_id, secret_id, affected_player_id)

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
        game = PlayService(db).end_game(game_id)
        if game.status == GameStatus.FINISHED:
            gameEndInfo = GameEndInfo(payload= db_game_2_game_end_info(game))
            await manager.broadcast(game.id, gameEndInfo.model_dump())
            return {"message": "The game has ended"}

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

@play_router.post(path="/{game_id}/actions/add-detective-to-set", status_code=200)
async def add_detective(
    game_id: int,
    turn_info: AddDetectiveInfo,
    db=Depends(get_db)
):
    game = GameService(db).get_by_id(game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No game found {game_id}",
        )
  
    player_id = turn_info.playerId
    set_id = turn_info.setId
    card_id = turn_info.cardId
    
    try:
        event = PlayService(db).add_detective(game, player_id, set_id, card_id)
        
        #NOTIFICACION DE CARTA AÑADIDA AL SET

        gamePublictInfo = PublicUpdate(payload=db_game_2_game_public_info(game))
        await manager.broadcast(game.id, gamePublictInfo.model_dump())

        playedCard = db_player_2_played_detective_info(event.main_player, event.played_card, ActionType.DETECTIVE, event.dset.player)
        await manager.broadcast_except(
            game_id=game.id, 
            exclude_player_id=event.main_player.id,
            message=playedCard.model_dump()
        )

        for player in game.players:
            playerPrivateInfo = PrivateUpdate(payload=db_player_2_player_private_info(player))

            await manager.send_to_player(
                game_id=game.id,
                player_id=player.id,
                message=playerPrivateInfo.model_dump()
            )
        
        if game.action_status is ActionStatus.UNBLOCKED:
                reset_timer(game_id, db)
        else:
        # RESOLVE NOT CANCELABLE EVENTS  
            EventManager(db).resolve(game.id)
            notifyEvent = DetectiveSetService(db).play_detective_select_event(game, card_id, event.dset)
            await manager.send_to_player(
                game_id=game.id,
                player_id=event.selected_player_id,
                message={"event": turn_action_enum_2_str(notifyEvent)}
            )       

            
    except PlayerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"player {player_id} not found",
        )
    except NotPlayersTurnError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"It's not the turn of player {player_id}",
        )
    except InvalididDetectiveSet as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a valid detective set. Learn the rules little cheater.",
    )  
