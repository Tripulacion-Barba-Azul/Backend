from sqlalchemy.orm import Session

from App.card.services import CardService
from App.exceptions import (
    DeckNotFoundError,
    GameNotFoundError,
    NotPlayersTurnError,
    PlayerHave6CardsError,
    PlayerNotFoundError)
from App.games.models import Game
from App.games.services import GameService
from App.players.models import Player
from App.players.enums import TurnStatus

class PlayService:

    def __init__(self, db: Session):
        self._db = db
        self._game_service = GameService(db)
        
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

        card = rep_deck.cards[0]

        CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id, commit=False)
        CardService(self._db).relate_card_player(player_id, card.id, commit=False)

        self._db.commit()
        self._db.refresh(rep_deck)
        self._db.refresh(player)
        self._db.refresh(card)

        return card