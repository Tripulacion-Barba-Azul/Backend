from sqlalchemy.orm import Session

from App.card.services import CardService
from App.decks.discard_deck_service import DiscardDeckService
from App.card.services import CardService
from App.decks.draft_deck_service import DraftDeckService
from App.exceptions import (
    GameNotFoundError,
    InvalididDetectiveSet,
    NotCardInHand,
    NotPlayableCard,
    NotPlayersTurnError,
    ObligatoryDiscardError,
    PlayerNeedSixCardsError,
    PlayerNotFoundError,
    PlayerHave6CardsError,
    DeckNotFoundError,
    SecretAlreadyRevealedError,
    SecretNotFoundError,
    SecretNotRevealed)
from App.games.models import Game
from App.games.services import GameService
from App.games.enums import GameStatus
from App.secret.services import relate_secret_player, reveal_secret, unrelate_secret_player
from App.players.models import Player
from App.players.enums import TurnAction, TurnStatus
from App.players.services import PlayerService
from App.sets.services import DetectiveSetService
from App.card.models import Card, Event

class PlayService:

    def __init__(self, db: Session):
        self._db = db
        self._game_service = GameService(db)
        self._player_service = PlayerService(db)
        self._card_service = CardService(db)
        self._discard_deck_service = DiscardDeckService(db)
        self._detective_set_service = DetectiveSetService(db)
        
    def no_action(
            self,
            game_id: int,
            player_id: int,
        ) -> Game:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")

        player: Player | None = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        
        player.turn_status = TurnStatus.DISCARDING
        
        self._db.add(player)
        self._db.flush()
        self._db.commit()
        
        return game
    
    def play_card(self, game, player_id, card_id) -> tuple[Card,TurnAction]:
        player = self._db.query(Player).filter(Player.id == player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        
        if card_id not in [card.id for card in player.cards]:
            raise NotCardInHand("That card does not belong to the player.")
        
        card = self._card_service.get_card(card_id)
        if not isinstance(card, Event):
            raise NotPlayableCard("You tried to play a card that is not playable.")
        
        self._card_service.unrelate_card_player(card_id, player_id)

        event = self._card_service.select_event_type(game, player, card)
        if event in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = event

        self._db.flush()
        self._db.commit()

        return card, event

    
    def play_set(self, game, player_id, card_ids):
        player = self._db.query(Player).filter(Player.id == player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        cards = player.cards
        
                
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        played_cards = [card for card in player.cards if card.id in card_ids]
        set_type = self._detective_set_service.validate_play_set(played_cards)
        if not set_type:
            raise InvalididDetectiveSet("Not a valid detective set. Learn the rules little cheater.")

        new_set = self._detective_set_service.create_detective_set(player_id, card_ids, set_type)
        
        event = self._detective_set_service.select_event_type(game, set_type)
        
        if event == TurnAction.NO_EFFECT:
            player.turn_action = TurnAction.NO_ACTION
            player.turn_status = TurnStatus.DISCARDING_OPT
        else :
            player.turn_action = event
            player.turn_status = TurnStatus.TAKING_ACTION


        self._db.flush()
        self._db.commit()

        return new_set
    
    def steal_set(
            self,
            player_id: int,
            stolen_player_id: int,
            set_id: int
    ):
        
        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        stolen_player = self._db.query(Player).filter(Player.id == stolen_player_id).first()
        if not stolen_player:
            raise PlayerNotFoundError(f"Player {stolen_player_id} not found")
        
        if set_id not in [dset.id for dset in stolen_player.sets]:
            raise InvalididDetectiveSet(f"Detective set {set_id} not found")
        
        dset = next((dset for dset in stolen_player.sets if dset.id == set_id))
        
        stolen_player.sets.remove(dset)
        player.sets.append(dset)

        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()

        return dset
    

    def discard(
            self,
            game: Game,
            player_id: int,
            cards_id: list[int]
        ):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_status not in [TurnStatus.DISCARDING, TurnStatus.DISCARDING_OPT]:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")

        if player.turn_status == TurnStatus.DISCARDING and len(cards_id) == 0:
            raise ObligatoryDiscardError(f"Player {player_id} must discard at least one card")

        for card_id in cards_id:
            card = self._card_service.get_card(card_id)
            card = self._player_service.discard_card(player_id, card)
            self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)

        player.turn_status = TurnStatus.DRAWING

        self._db.add(player)
        self._db.flush()
        self._db.commit()


    def draw_card_from_deck(self, game_id, player_id):

        game = self._db.query(Game).filter_by(id=game_id).first()
        rep_deck = game.reposition_deck # type: ignore
        player = self._db.query(Player).filter_by(id=player_id).first()

        if player.turn_status != TurnStatus.DRAWING: # type: ignore
            raise NotPlayersTurnError(f"It's not the turn of player {player_id} for discard")

        if rep_deck is None:
            raise DeckNotFoundError(f"Game {game_id} doesn't have a reposition deck")  
        
        if player is None:
            raise PlayerNotFoundError(f"Player {player_id} not found")  
              
        if len(player.cards) == 6:
            raise PlayerHave6CardsError(f"Player {player_id} already has 6 cards")

        if rep_deck.number_of_cards == 0:
            return None

        card = max(rep_deck.cards, key=lambda c: c.order)  # type: ignore

        CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id, commit=True)
        CardService(self._db).relate_card_player(player_id, card.id, commit=True)

        self._db.commit()
        self._db.refresh(rep_deck)
        self._db.refresh(player)
        self._db.refresh(card)

        return card

    def end_turn(
            self,
            game_id: int,
            player_id: int,
        ) -> tuple[Game, Player]:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game: 
            raise GameNotFoundError(f"No game found {game_id}")

        player: Player | None = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.DRAWING:
            raise NotPlayersTurnError(f"Player {player_id} cannot end turn now")
        if len(player.cards) != 6:
            raise PlayerNeedSixCardsError(f"Player {player_id} needs to have six cards to end turn")
        
        player.turn_status = TurnStatus.WAITING
        game.turn_number += 1
        
        GameService(self._db).select_player_turn(game_id)
        
        self._db.add(player)
        self._db.add(game)
        self._db.flush()
        self._db.commit()

        return game, player
    
    def end_game(self, game_id: int) -> Game:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")

        deck = game.reposition_deck
        if len(deck.cards) == 0:
            game.status = GameStatus.FINISHED
            
        self._db.add(game)
        self._db.flush()
        self._db.commit()

        return game


    def draw_card_from_draft(self, game_id, player_id, order):
        game = self._db.query(Game).filter_by(id=game_id).first()
        draft_deck = game.draft_deck
        rep_deck = game.reposition_deck
        player = self._db.query(Player).filter_by(id=player_id).first()


        if player.turn_status != TurnStatus.DRAWING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id} for discard")

        if draft_deck is None:
            raise DeckNotFoundError(f"Game {game_id} doesn't have a draft deck")  
        
        if player is None:
            raise PlayerNotFoundError(f"Player {player_id} not found")  
              
        card = None
        for c in draft_deck.cards:
            if c.order == order:
                card = c
                break
        

        DraftDeckService(self._db).unrelate_card_from_draft_deck(draft_deck.id, card)
        CardService(self._db).relate_card_player(player_id, card.id, commit=True)

        self._db.commit()
        self._db.refresh(draft_deck)
        self._db.refresh(player)
        self._db.refresh(card)

        card1 = max(rep_deck.cards, key=lambda c: c.order)  # type: ignore
        CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card1.id, commit=True)
        DraftDeckService(self._db).relate_card_to_draft_deck(draft_deck.id, card1, order)

        self._db.commit()
        self._db.refresh(draft_deck)
        self._db.refresh(rep_deck)
        self._db.refresh(card1)

        return card

    def reveal_secret_service(self, player_id: int, secret_id: int, revealed_player_id: int):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        revealed_player = self._db.query(Player).filter(Player.id == revealed_player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if not revealed_player:
            raise PlayerNotFoundError(f"Player {revealed_player_id} not found")

        if player.turn_status != TurnStatus.TAKING_ACTION:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")

        if player.turn_action != TurnAction.REVEAL_SECRET:
            raise NotPlayersTurnError(f"Player {player_id} cannot reveal secret now")

        secret = None
        for s in revealed_player.secrets:
            if s.id == secret_id:
                secret = s
                break
        
        if not secret:
            raise SecretNotFoundError(f"Secret {secret_id} not found for player {player_id}")
        
        if secret.revealed:
            raise SecretAlreadyRevealedError(f"Secret {secret_id} already revealed")

        reveal_secret(secret, self._db)
    
        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.commit()
        self._db.refresh(player)
        self._db.refresh(secret)
        self._db.refresh(revealed_player)

        return secret

    def hide_secret(self, player_id, secret_id, affected_player_id):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_action != TurnAction.HIDE_SECRET:
            raise NotPlayersTurnError(f"Player {player_id} cannot hide secret now")
        
        affected_player = self._db.query(Player).filter(Player.id == affected_player_id).first()
        if not affected_player:
            raise PlayerNotFoundError(f"Player {affected_player_id} not found")
        
        if secret_id not in [secret.id for secret in affected_player.secrets]:
            raise SecretNotFoundError(f"Secret id {secret_id} not found")
        
        secret = next((secret for secret in affected_player.secrets if secret.id == secret_id))

        if not secret.revealed:
            raise SecretNotRevealed(f"Secret id {secret_id} is not revealed")
        
        secret.revealed = False
        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        # TODO: si affected_played_id esta en desgracia social quitarsela

        self._db.flush()
        self._db.commit()
        
        return secret.id