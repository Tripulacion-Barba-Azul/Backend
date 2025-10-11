from sqlalchemy.orm import Session

from App.decks.discard_deck_model import DiscardDeck
from App.decks.discard_deck_service import DiscardDeckService
from App.decks.reposition_deck_model import RepositionDeck
from App.games.models import Game
from App.card.services import CardService
from App.games.models import Game
import random
from App.decks.constants import (
    detective_cards,
    event_cards,
    devious_cards,
    event_cards_2,
    devious_cards_2
)
from App.players.models import Player


class RepositionDeckService:


    def __init__(self, db: Session):
        self._db = db  

    def get_reposition_deck(self, deck_id):
        rep_deck = self._db.query(RepositionDeck).filter_by(id = deck_id).first()
        if rep_deck == None:
            raise ValueError(
                f"Deck with id:{deck_id} dont exist"
            )
        else:
            return rep_deck




    def relate_reposition_deck_game(self, deck_id, game_id):

        rep_deck = self.get_reposition_deck(deck_id)
        game = self._db.query(Game).filter_by(id = game_id).first()

        if game == None:
            raise ValueError(
                f"Game with id {game_id} dont exist"
            )
        else:
            game.reposition_deck = rep_deck
            self._db.commit()
            self._db.refresh(rep_deck)
            self._db.refresh(game)


    def create_reposition_deck(self, game_id: int):
        deck = list()
        rep_deck = RepositionDeck()
        self._db.add(rep_deck)
        self._db.commit()
        self._db.refresh(rep_deck)

        game = self._db.query(Game).filter_by(id=game_id).first()

        if game is None:
            raise ValueError(f"Game with id {game_id} does not exist") 

        if game.reposition_deck is not None:
            raise ValueError(f"Game {game_id} already has a reposition deck")
        
        player_number = len(game.players)
        
        for cantidad, card_name, card_effect, number_to_set in detective_cards:
            for i in range(cantidad):
                deck.append(CardService(self._db).create_detective_card(card_name, card_effect, number_to_set))

        if player_number >2:  

            for cantidad, card_name, card_effect in event_cards:
                for j in range(cantidad):
                    deck.append(CardService(self._db).create_event_card(card_name, card_effect))
            
            for cantidad, card_name, card_effect in devious_cards:
                for n in range(cantidad):
                    deck.append(CardService(self._db).create_devious_card(card_name, card_effect))

        else:
            for cantidad, card_name, card_effect in event_cards_2:
                for j in range(cantidad):
                    deck.append(CardService(self._db).create_event_card(card_name, card_effect))
            
            for cantidad, card_name, card_effect in devious_cards_2:
                for n in range(cantidad):
                    deck.append(CardService(self._db).create_devious_card(card_name, card_effect))


        
        not_so_fast_cards = list()
        for m in range(10):
            not_so_fast_cards.append(CardService(self._db).create_instant_card("Not so Fast!", ""))

        
        for i, player in enumerate(game.players):
            card = not_so_fast_cards[i]
            CardService(self._db).relate_card_player(player.id, card.id, commit=False)

        
        for i in range(player_number, 10):
            deck.append(not_so_fast_cards[i])

        random.shuffle(deck)

        for card in deck:
            CardService(self._db).relate_card_reposition_deck(rep_deck.id, card.id, commit=False)



        self._db.commit()
        self._db.refresh(rep_deck)

        for player in game.players:
            self._db.refresh(player)

        self.relate_reposition_deck_game(rep_deck.id, game_id)
        return rep_deck



    def draw_reposition_deck(self, game_id):
        game = self._db.query(Game).filter_by(id=game_id).first()
        rep_deck = game.reposition_deck # type: ignore

        if rep_deck is None:
            raise ValueError(f"Game {game_id} doesn't have a reposition deck")    
        
        
        players = game.players # type: ignore
        cards_needed = 5 * len(players)
        
        if len(rep_deck.cards) < cards_needed:
            raise ValueError(f"Not enough cards in reposition deck")
        


        for player in players:
            while len(player.cards) < 6: 
                card = max(rep_deck.cards, key=lambda c: c.order)  # type: ignore
                CardService(self._db).relate_card_player(player.id, card.id, commit=False)
                CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id, commit=False)

        
        self._db.commit()
        
        self._db.refresh(rep_deck)
        for player in players:
            self._db.refresh(player)

        if rep_deck.cards != []:
            card = max(rep_deck.cards, key=lambda c: c.order)

        CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id, commit=True)

        
        discard_pile = DiscardDeckService(self._db).create_discard_deck()
        DiscardDeckService(self._db).relate_card_to_discard_deck(discard_pile.id, card)
        DiscardDeckService(self._db).relate_discard_deck_game(discard_pile.id, game.id)

        self._db.refresh(discard_pile)



    