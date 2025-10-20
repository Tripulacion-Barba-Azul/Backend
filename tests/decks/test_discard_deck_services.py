from pytest import Session
import pytest

from App.card.models import Card
from App.decks.discard_deck_model import DiscardDeck
from App.decks.discard_deck_service import DiscardDeckService


def test_get_discard_deck_success(session:Session):
        """Test obtener un DiscardDeck existente"""

        sample_deck = DiscardDeckService(session).create_discard_deck()
        
        deck = DiscardDeckService(session).get_discard_deck(sample_deck.id)
        
        assert deck is not None
        assert (deck.id) == (sample_deck.id)
        assert isinstance(deck, DiscardDeck)

def test_get_nonexistent_discard_deck(session:Session):
        """Test que al intentar obtener un deck inexistente lanza error"""
        
        with pytest.raises(ValueError, match="Deck with id: 999 dont exist"):
            DiscardDeckService(session).get_discard_deck(999)

def test_create_discard_deck_success(session:Session):
    """Test de crear mazo de descarte"""
    dis_deck = DiscardDeckService(session).create_discard_deck()

    assert dis_deck is not None 
    assert isinstance(dis_deck, DiscardDeck)
    assert dis_deck.id is not None


def test_relate_discard_deck_game_success(session:Session, sample_game):
    """Test de relacionar mazo de descarte con juego"""
    game = sample_game
    dis_deck = DiscardDeckService(session).create_discard_deck()
    DiscardDeckService(session).relate_discard_deck_game(dis_deck.id, game.id)

    assert dis_deck.game is not None
    assert dis_deck.game.id == game.id
    assert game.discard_deck.id == dis_deck.id

def test_relate_discard_deck_game_nonexistent_game(session:Session):
    """Test de relacionar mazo de descarte con juego inexistente"""
    dis_deck = DiscardDeckService(session).create_discard_deck()
    
    with pytest.raises(ValueError, match="Game with id: 999 dont exist"):
        DiscardDeckService(session).relate_discard_deck_game(dis_deck.id, 999)


def test_relate_card_to_discard_deck_success(session:Session):
    """Test de relacionar carta a mazo de descarte"""

    dis_deck = DiscardDeckService(session).create_discard_deck()
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "detective"
    )

    DiscardDeckService(session).relate_card_to_discard_deck(dis_deck.id, card)

    assert dis_deck.cards[0].id == card.id
    assert dis_deck.number_of_cards == 1
    assert card.order == 1


def test_relate_card_to_discard_deck_nonexistent_deck(session:Session):
    """Test de relacionar carta a mazo de descarte inexistente"""
    
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "detective"
    )

    with pytest.raises(ValueError, match="Deck with id: 999 dont exist"):
        DiscardDeckService(session).relate_card_to_discard_deck(999, card)