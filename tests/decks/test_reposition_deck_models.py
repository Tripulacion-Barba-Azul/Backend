import pytest

from sqlalchemy.orm import Session
from App.decks.reposition_deck_model import RepositionDeck
from datetime import date
from App.card.models import Card
from App.games.models import Game
from App.players.models import Player



@pytest.fixture
def sample_player(session:Session):
    player = Player(name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player



def test_create_reposition_deck(session:Session):

    rep_deck= RepositionDeck()

    session.add(rep_deck)
    session.commit()
    session.refresh(rep_deck)

    assert rep_deck is not None
    assert rep_deck.cards == []
    assert rep_deck.id is not None
    assert isinstance (rep_deck.id, int)




def test_relationship_with_cards(session:Session):
    rep_deck= RepositionDeck()
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "detective"
    )

    rep_deck.cards.append(card)
    session.add(card)
    session.add(rep_deck)
    session.commit()
    session.refresh(rep_deck)
    session.refresh(card)

    assert len(rep_deck.cards) == 1
    assert card.reposition_deck[0].id == rep_deck.id




def test_relationship_with_game(session:Session, sample_player):
    rep_deck= RepositionDeck()
    
    game = Game(
        name = "game_name",
        min_players = 2,
        max_players = 4,
        owner = sample_player,
    )

    session.add(rep_deck)
    session.add(game)
    session.commit()
    session.refresh(rep_deck)
    session.refresh(game)

    game.reposition_deck= rep_deck
    
    session.commit()
    session.refresh(rep_deck)
    session.refresh(game)

    assert game.reposition_deck.id == rep_deck.id
    assert rep_deck.game_id == game.id


