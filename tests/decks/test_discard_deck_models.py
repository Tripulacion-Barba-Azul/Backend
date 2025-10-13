from datetime import date
from pytest import Session

from App.card.models import Card
from App.decks.discard_deck_model import DiscardDeck
from App.games.models import Game


def test_create_reposition_deck(session:Session):

    dis_deck= DiscardDeck()

    session.add(dis_deck)
    session.commit()
    session.refresh(dis_deck)

    assert dis_deck is not None
    assert dis_deck.cards == []
    assert dis_deck.id is not None
    assert isinstance (dis_deck.id, int)

def test_relationship_with_cards(session:Session):
    dis_deck= DiscardDeck()
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "detective"
    )

    dis_deck.cards.append(card)
    session.add(card)
    session.add(dis_deck)
    session.commit()
    session.refresh(dis_deck)
    session.refresh(card)

    assert len(dis_deck.cards) == 1
    assert card.discard_deck[0].id == card.id


def test_relationship_with_game(session:Session, sample_game):

    dis_deck= DiscardDeck()
    game = sample_game

    game.discard_deck = dis_deck

    session.add(game)
    session.add(dis_deck)
    session.commit()
    session.refresh(dis_deck)
    session.refresh(game)

    assert dis_deck.game is not None
    assert dis_deck.game.id == game.id
    assert game.discard_deck.id == dis_deck.id