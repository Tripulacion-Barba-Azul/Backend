from sqlalchemy.orm import Session

from App.decks.discard_deck_model import DiscardDeck
from App.games.models import Game

class DiscardDeckService:

    def __init__(self, db: Session):
        self._db = db
    

    def get_discard_deck(self, deck_id):
        discard_deck = self._db.query(DiscardDeck).filter_by(id = deck_id).first()
        if discard_deck == None:
            raise ValueError(f"Deck with id: {deck_id} dont exist")
        else:
            return discard_deck
        
    def create_discard_deck(self):
        discard_deck = DiscardDeck()
        self._db.add(discard_deck)
        self._db.commit()
        self._db.refresh(discard_deck)
        return discard_deck
    
    def relate_discard_deck_game(self, deck_id, game_id):

        discard_deck = self.get_discard_deck(deck_id)
        game = self._db.query(Game).filter_by(id = game_id).first()

        if game == None:
            raise ValueError(
                f"Game with id: {game_id} dont exist"
            )

        game.discard_deck = discard_deck
        self._db.commit()
        self._db.refresh(discard_deck)
        self._db.refresh(game)


    def relate_card_to_discard_deck(self, deck_id, card):

        discard_deck = self.get_discard_deck(deck_id)


        discard_deck.number_of_cards += 1
        card.order = discard_deck.number_of_cards
        discard_deck.cards.append(card)
        self._db.commit()
        self._db.refresh(discard_deck)
        return discard_deck
