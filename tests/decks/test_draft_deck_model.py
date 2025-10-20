
from pytest import Session

from App.card.models import Card
from App.decks.draft_deck_model import DraftDeck
from App.games.models import Game


def test_create_draft_deck(session:Session):
    draft_deck= DraftDeck()

    session.add(draft_deck)
    session.commit()
    session.refresh(draft_deck)

    assert draft_deck is not None
    assert draft_deck.cards == []
    assert draft_deck.id is not None
    assert isinstance (draft_deck.id, int)

def test_relate_card_to_draft_deck(session:Session):
    draft_deck= DraftDeck()
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "detective"
    )

    draft_deck.cards.append(card)
    session.add(card)
    session.add(draft_deck)
    session.commit()
    session.refresh(draft_deck)
    session.refresh(card)

    assert len(draft_deck.cards) == 1
    assert draft_deck.cards[0].id == draft_deck.id

def test_relate_draft_deck_game(session:Session, sample_game):
    draft_deck= DraftDeck()
    
    game = sample_game

    session.add(game)
    session.add(draft_deck)
    session.commit()
    session.refresh(draft_deck)
    session.refresh(game)

    game.draft_deck = draft_deck
    
    session.commit()
    session.refresh(draft_deck)
    session.refresh(game)

    assert game.draft_deck.id == draft_deck.id
    assert draft_deck.game.id == game.id