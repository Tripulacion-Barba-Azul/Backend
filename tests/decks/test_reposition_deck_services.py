import pytest

from sqlalchemy.orm import Session
from App.decks.reposition_deck_model import RepositionDeck
from datetime import date
from App.card.models import Card
from App.games.models import Game
from App.players.models import Player
from App.decks.reposition_deck_services import *



@pytest.fixture
def sample_player(session:Session):
    player = Player(name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture
def sample_game(session, sample_player):
    """Fixture para crear un game de prueba"""
    game = Game(
        name="test_game",
        min_players=2,
        max_players=4,
        owner= sample_player
    )
    session.add(game)
    session.commit()
    session.refresh(game)
    return game

@pytest.fixture
def sample_reposition_deck(session):
    """Fixture para crear un RepositionDeck de prueba"""
    deck = RepositionDeck()
    session.add(deck)
    session.commit()
    session.refresh(deck)
    return deck



def test_get_existing_reposition_deck(session:Session, sample_reposition_deck):
        """Test obtener un RepositionDeck existente"""
        
        rep_deck = get_reposition_deck(sample_reposition_deck.id, session)
        
        assert rep_deck is not None
        assert rep_deck.id == sample_reposition_deck.id
        assert isinstance(rep_deck.cards, list)


def test_get_nonexistent_reposition_deck(session:Session):
        """Test que al intentar obtener un deck inexistente lanza error"""
        
        with pytest.raises(ValueError, match="Deck with id:999 dont exist"):
            get_reposition_deck(999, session)



def test_create_repposition_deck_success(sample_game, session:Session):
    """Test de crear mazo de reposicion"""
    game = sample_game
    rep_deck = create_reposition_deck(game.id,session)

    assert rep_deck is not None 
    assert rep_deck.game_id == game.id

    detective_count = len(session.query(Detective).filter_by(type = "detective").all())
    devious_count = len(session.query(Card).filter_by(type = "devious").all())
    instant_count = len(session.query(Card).filter_by(type = "instant").all())
    event_count = len(session.query(Card).filter_by(type = "event").all())

    assert detective_count == 25
    assert devious_count == 4
    assert instant_count == 10 
    assert event_count == 22

def test_reposition_deck_unsuccess(sample_game, session:Session):
    """Test que al crear un deck a una partida con un deck creado lanza error"""
    rep_deck1 = create_reposition_deck(sample_game.id,session)
    with pytest.raises(ValueError, match=f"Game {sample_game.id} already has a reposition deck"):
            create_reposition_deck(sample_game.id,session)


def test_draw_reposition_deck_sucess(sample_player,sample_game, session:Session):
    """Test de repartir mazo de reposicion"""
    create_reposition_deck(sample_game.id, session)
    sample_game.players.append(sample_player)
    draw_reposition_deck(sample_game.id, session)

    
    print(sample_player.cards)
    assert len(sample_player.cards) == 6




