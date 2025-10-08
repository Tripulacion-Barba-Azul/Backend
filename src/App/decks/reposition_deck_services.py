from sqlalchemy.orm import Session

from App.decks.reposition_deck_model import RepositionDeck
from App.games.models import Game
from App.card.services import *
from App.games.models import Game
import random

def get_reposition_deck(deck_id, db:Session):
    rep_deck = db.query(RepositionDeck).filter_by(id = deck_id).first()
    if rep_deck == None:
        raise ValueError(
            f"Deck with id:{deck_id} dont exist"
        )
    else:
        return rep_deck




def relate_reposition_deck_game(deck_id, game_id, db:Session):

    rep_deck = get_reposition_deck(deck_id, db)
    game = db.query(Game).filter_by(id = game_id).first()

    if game == None:
        raise ValueError(
            f"Game with id {game_id} dont exist"
        )
    else:
        game.reposition_deck = rep_deck
        db.commit()
        db.refresh(rep_deck)
        db.refresh(game)



detective_cards = [
    (3,"Hercule Poirot", "", 3),
    (3, "Miss Marple", "", 3),
    (2, "Mr Sattertwhaite", "",2),
    (3,"Ariadne Oliver","", 0),
    (2,"Tuppence Beresford", "",2),
    (2,"Tommy Beresford", "",2),
    (3, "Lady Eileen Brent", "",2),
    (4, "Harley Quin","",0),
    (3, "Parker Pyne","",2)
]



event_cards = [
    (1, "Cards off the table", ""),
    (2, "Another Victim",""),
    (3, "Dead Card Folly", ""),
    (3, "Look in to the Ashes", ""),
    (3, "Card Trade", ""),
    (2, "And There was One More...",""),
    (3, "Delay the Muderer's Escape", ""),
    (2, "Early Train to Paddington", ""),
    (3, "Point Your Suspicions","")

]



devious_cards =[
    (1, "Blackmailed!",""),
    (3, "Social Faux Pas", "")
]


def create_reposition_deck(game_id: int, db: Session):
    deck = list()
    rep_deck = RepositionDeck()
    db.add(rep_deck)
    db.commit()
    db.refresh(rep_deck)

    
    for cantidad, card_name, card_effect, number_to_set in detective_cards:
        for i in range(cantidad):
            deck.append(create_detective_card(card_name, card_effect, number_to_set, db))
            
    for cantidad, card_name, card_effect in event_cards:
        for j in range(cantidad):
            deck.append(create_event_card(card_name, card_effect, db))
    
    for cantidad, card_name, card_effect in devious_cards:
        for n in range(cantidad):
            deck.append(create_devious_card(card_name, card_effect, db))

    game = db.query(Game).filter_by(id=game_id).first()
    if game is None:
        raise ValueError(f"Game with id {game_id} does not exist") 

    if game.reposition_deck is not None:
        raise ValueError(f"Game {game_id} already has a reposition deck")
    
    player_number = len(game.players)

    
    not_so_fast_cards = list()
    for m in range(10):
        not_so_fast_cards.append(create_instant_card("Not so Fast!", "", db))

    
    for i, player in enumerate(game.players):
        card = not_so_fast_cards[i]
        relate_card_player(player.id, card.id, db, commit=False)

    
    for i in range(player_number, 10):
        deck.append(not_so_fast_cards[i])

    rep_deck.cards = deck
    

    db.commit()
    db.refresh(rep_deck)

    for player in game.players:
        db.refresh(player)

    relate_reposition_deck_game(rep_deck.id, game_id, db)
    return rep_deck



def draw_reposition_deck(game_id, db: Session):
    game = db.query(Game).filter_by(id=game_id).first()
    rep_deck = game.reposition_deck # type: ignore

    if rep_deck is None:
        raise ValueError(f"Game {game_id} doesn't have a reposition deck")    
    
    
    players = game.players # type: ignore
    cards_needed = 5 * len(players)
    
    if len(rep_deck.cards) < cards_needed:
        raise ValueError(f"Not enough cards in reposition deck")
    
    deck_copy = rep_deck.cards.copy()
    random.shuffle(deck_copy)


    for player in players:
        while len(player.cards) < 6: 
            card = deck_copy.pop(0)
            relate_card_player(player.id, card.id, db, commit=False)
            unrelate_card_reposition_deck(rep_deck.id, card.id, db, commit=False)

    
    db.commit()
    
    db.refresh(rep_deck)
    for player in players:
        db.refresh(player)



