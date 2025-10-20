

from pytest import Session
import pytest
from App.card.models import Card
from App.decks.draft_deck_service import DraftDeckService

def test_create_draft_deck(session: Session):
    """Test de crear mazo de draft"""
    draft_deck = DraftDeckService(session).create_draft_deck()

    assert draft_deck is not None
    assert draft_deck.cards == []
    assert draft_deck.id is not None
    assert isinstance(draft_deck.id, int)

def test_get_draft_deck(session: Session):
    """Test obtener un DraftDeck existente"""
    draft_deck1 = DraftDeckService(session).create_draft_deck()
    draft_deck = DraftDeckService(session).get_draft_deck(draft_deck1.id)

    assert draft_deck is not None
    assert draft_deck.id == draft_deck1.id
    assert isinstance(draft_deck.cards, list)

def test_get_nonexistent_draft_deck(session: Session):
    """Test que al intentar obtener un deck inexistente lanza error"""

    with pytest.raises(ValueError, match="Deck with id: 999 dont exist"):
        DraftDeckService(session).get_draft_deck(999)

def test_relate_draft_deck_game(session: Session, sample_game):
    """Test de relacionar un draft deck a un game"""
    draft_deck = DraftDeckService(session).create_draft_deck()
    game = sample_game

    DraftDeckService(session).relate_draft_deck_game(draft_deck.id, game.id)

    assert game.draft_deck.id == draft_deck.id
    assert draft_deck.game.id == game.id    

def test_relate_card_to_draft_deck(session: Session):
    """Test de relacionar una carta a un draft deck"""
    draft_deck = DraftDeckService(session).create_draft_deck()
    from App.card.models import Card
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "detective"
    )

    draft_deck = DraftDeckService(session).relate_card_to_draft_deck(draft_deck.id, card, 1)

    assert draft_deck.cards[0].id == card.id
    assert draft_deck.number_of_cards == 1 
    assert card.order == 1

def test_relate_card_to_full_draft_deck(session: Session):
    """Test de relacionar una carta a un draft deck lleno"""
    draft_deck = DraftDeckService(session).create_draft_deck()
    
    card1 = Card(
        name = "test_Card1",
        effect = "test_effect1",
        type = "detective"
    )
    card2 = Card(
        name = "test_Card2",
        effect = "test_effect2",
        type = "detective"
    )
    card3 = Card(
        name = "test_Card3",
        effect = "test_effect3",
        type = "detective"
    )
    card4 = Card(
        name = "test_Card4",
        effect = "test_effect4",
        type = "detective"
    )

    draft_deck = DraftDeckService(session).relate_card_to_draft_deck(draft_deck.id, card1, 1)
    draft_deck = DraftDeckService(session).relate_card_to_draft_deck(draft_deck.id, card2, 2)
    draft_deck = DraftDeckService(session).relate_card_to_draft_deck(draft_deck.id, card3, 3)

    with pytest.raises(ValueError, match=f"Draft deck with id: {draft_deck.id} is full"):
        DraftDeckService(session).relate_card_to_draft_deck(draft_deck.id, card4, 4)   

def test_unrelate_card_from_draft_deck(session: Session): 
    """Test de desrelacionar una carta de un draft deck"""
    draft_deck = DraftDeckService(session).create_draft_deck()
    
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "detective"
    )

    draft_deck = DraftDeckService(session).relate_card_to_draft_deck(draft_deck.id, card, 1)
    assert draft_deck.number_of_cards == 1 
    assert card in draft_deck.cards

    draft_deck = DraftDeckService(session).unrelate_card_from_draft_deck(draft_deck.id, card)

    assert draft_deck.number_of_cards == 0
    assert card not in draft_deck.cards

def test_unrelate_nonexistent_card_from_draft_deck(session: Session):
    """Test de desrelacionar una carta que no esta en el draft deck"""
    draft_deck = DraftDeckService(session).create_draft_deck()
    
    card1 = Card(
        name = "test_Card1",
        effect = "test_effect1",
        type = "detective"
    )
    card2 = Card(
        name = "test_Card2",
        effect = "test_effect2",
        type = "detective"
    )

    draft_deck = DraftDeckService(session).relate_card_to_draft_deck(draft_deck.id, card1, 1)
    assert draft_deck.number_of_cards == 1 

    with pytest.raises(ValueError, match=f"Card with id: {card2.id} is not in draft deck with id: {draft_deck.id}"):
        DraftDeckService(session).unrelate_card_from_draft_deck(draft_deck.id, card2)


