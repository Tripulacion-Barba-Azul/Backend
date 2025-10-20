from sqlalchemy.orm import Session
from App.decks.draft_deck_model import DraftDeck
from App.games.models import Game

class DraftDeckService: 
    def __init__(self, db: Session):
        self._db = db

    def get_draft_deck(self, deck_id):
        draft_deck = self._db.query(DraftDeck).filter_by(id = deck_id).first()
        if draft_deck == None:
            raise ValueError(f"Deck with id: {deck_id} dont exist")
        else:
            return draft_deck

    def create_draft_deck(self):
        draft_deck = DraftDeck()
        self._db.add(draft_deck)
        self._db.commit()
        self._db.refresh(draft_deck)
        return draft_deck

    def relate_draft_deck_game(self, deck_id, game_id):

        draft_deck = self.get_draft_deck(deck_id)
        game = self._db.query(Game).filter_by(id = game_id).first()

        if game == None:
            raise ValueError(
                f"Game with id: {game_id} dont exist"
            )

        game.draft_deck = draft_deck
        self._db.commit()
        self._db.refresh(draft_deck)
        self._db.refresh(game)

    def relate_card_to_draft_deck(self, deck_id, card, card_order):

        draft_deck = self.get_draft_deck(deck_id)
        if draft_deck.number_of_cards == 3:
            raise ValueError(
                f"Draft deck with id: {deck_id} is full"
            )

        draft_deck.number_of_cards += 1
        card.order = card_order
        draft_deck.cards.insert((card_order - 1), card)
        self._db.commit()
        self._db.refresh(draft_deck)
        return draft_deck

    def unrelate_card_from_draft_deck(self, deck_id, card):

        draft_deck = self.get_draft_deck(deck_id)
        if card not in draft_deck.cards:
            raise ValueError(
                f"Card with id: {card.id} is not in draft deck with id: {deck_id}"
            )

        draft_deck.cards.remove(card)
        draft_deck.number_of_cards -= 1
        self._db.commit()
        self._db.refresh(draft_deck)
        return draft_deck