from sqlalchemy.orm import Session

from App.card.services import CardService
from App.decks.discard_deck_service import DiscardDeckService
from App.card.services import CardService
from App.exceptions import (
    GameNotFoundError,
    InvalididDetectiveSet,
    NotPlayersTurnError,
    ObligatoryDiscardError,
    PlayerNeedSixCardsError,
    PlayerNotFoundError,
    PlayerHave6CardsError,
    DeckNotFoundError)
from App.games.models import Game
from App.games.services import GameService
from App.games.enums import GameStatus
from App.players.models import Player
from App.players.enums import TurnAction, TurnStatus
from App.players.services import PlayerService
from App.sets.services import DetectiveSetService

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
    
    def play_set(self, player_id, card_ids):
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

        player.turn_status = TurnStatus.TAKING_ACTION

        player.turn_action = self._detective_set_service.select_event_type(set_type)


        self._db.flush()
        self._db.commit()

        return new_set
    
    def play_event(self, player_id, event_card_id):
        player = self._db.query(Player).filter(Player.id == player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        if player.turn_action != TurnAction.NO_ACTION:
            raise NotPlayersTurnError(f"Player {player_id} cannot play an event now")
        
        event_card = self._card_service.get_card(event_card_id)
        if event_card not in player.cards:
            raise PlayerNotFoundError(f"Player {player_id} does not have the card {event_card_id}")
        if event_card.type != "event":
            raise PlayerNotFoundError(f"Card {event_card_id} is not an event card")
        
        if event_card.name == "Cards off the table":
            player = self._player_service.discard_card(player_id, event_card)
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = TurnAction.CARDS_OFF_THE_TABLE
            
            self._db.add(player)
            self._db.flush()
            self._db.commit()

        return event_card
    

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
        rep_deck = game.reposition_deck
        player = self._db.query(Player).filter_by(id=player_id).first()

        if player.turn_status != TurnStatus.DRAWING:
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

    def select_any_player(self, game_id: int, player_id: int, selected_player_id: int) -> tuple[Game, Player, Player]:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")

        player: Player | None = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.TAKING_ACTION:
            raise NotPlayersTurnError(f"Player {player_id} cannot select any player now")
        if (player.turn_action != TurnAction.SELECT_ANY_PLAYER_SETS) or (player.turn_action != TurnAction.CARDS_OFF_THE_TABLE):
            raise NotPlayersTurnError(f"Player {player_id} cannot select any player now")
        player_in_game = GameService(self)._game_service.player_in_game(game_id, selected_player_id)
        if not player_in_game:
            raise PlayerNotFoundError(f"Selected player {selected_player_id} not found in game {game_id}")
        
        selected_player: Player | None = self._db.query(Player).filter(Player.id == selected_player_id).first()
        if not selected_player:
            raise PlayerNotFoundError(f"Selected player {selected_player_id} not found")
        selected_player_in_game = GameService(self)._game_service.player_in_game(game_id, selected_player_id)
        if not selected_player_in_game:
            raise PlayerNotFoundError(f"Selected player {selected_player_id} not found in game {game_id}")
        

        return game, player, selected_player
    
    def cards_off_the_tables(self, game: Game, player: Player, selected_player: Player) -> int:
        CountNotSoFast = 0

        cards_player = selected_player.cards
        for card in cards_player:
            if card.name == "Not so fast!":
                card = self._card_service.get_card(card.id)
                card = self._player_service.discard_card(player.id, card)
                self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)
                CountNotSoFast += 1
        
        player.turn_action = TurnAction.NO_ACTION
        player.turn_status = TurnStatus.DISCARDING_OPT
        self._db.add(player)
        self._db.flush()
        self._db.commit()
        
        return CountNotSoFast