import pytest

from sqlalchemy.orm import Session
from App.decks.reposition_deck_model import RepositionDeck
from datetime import date
from App.card.models import Card
from App.games.models import Game
from App.players.models import Player
from App.decks.reposition_deck_services import RepositionDeckService


@pytest.fixture
def sample_player(session:Session):
    player = Player(name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player



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
        
        rep_deck = RepositionDeckService(session).get_reposition_deck(sample_reposition_deck.id)
        
        assert rep_deck is not None
        assert rep_deck.id == sample_reposition_deck.id
        assert isinstance(rep_deck.cards, list)


def test_get_nonexistent_reposition_deck(session:Session):
        """Test que al intentar obtener un deck inexistente lanza error"""
        
        with pytest.raises(ValueError, match="Deck with id:999 dont exist"):
            RepositionDeckService(session).get_reposition_deck(999)



def test_create_repposition_deck_success_less_2(sample_game, session:Session):
    """Test de crear mazo de reposicion"""
    game = sample_game
    rep_deck = RepositionDeckService(session).create_reposition_deck(game.id)

    assert rep_deck is not None 
    assert rep_deck.game_id == game.id

    detective_count = len(session.query(Card).filter_by(type = "detective").all())
    devious_count = len(session.query(Card).filter_by(type = "devious").all())
    instant_count = len(session.query(Card).filter_by(type = "instant").all())
    event_count = len(session.query(Card).filter_by(type = "event").all())

    assert detective_count == 25
    assert devious_count == 3
    assert instant_count == 10 
    assert event_count == 19


def test_create_repposition_deck_success_more_2(sample_game, session:Session):
    """Test de crear mazo de reposicion"""
    game = sample_game
    game.players.append(Player(name="Jugador1", avatar="avatar1", birthday=date(1990,1,1)))
    game.players.append(Player(name="Jugador2", avatar="avatar2", birthday=date(1990,1,1)))
    rep_deck = RepositionDeckService(session).create_reposition_deck(game.id)

    assert rep_deck is not None 
    assert rep_deck.game_id == game.id

    detective_count = len(session.query(Card).filter_by(type = "detective").all())
    devious_count = len(session.query(Card).filter_by(type = "devious").all())
    instant_count = len(session.query(Card).filter_by(type = "instant").all())
    event_count = len(session.query(Card).filter_by(type = "event").all())

    assert detective_count == 25
    assert devious_count == 4
    assert instant_count == 10 
    assert event_count == 22


def test_reposition_deck_unsuccess(sample_game, session:Session):

    """Test que al crear un deck a una partida con un deck creado lanza error"""
    rep_deck1 = RepositionDeckService(session).create_reposition_deck(sample_game.id)
    with pytest.raises(ValueError, match=f"Game {sample_game.id} already has a reposition deck"):
            RepositionDeckService(session).create_reposition_deck(sample_game.id)


def test_draw_reposition_deck_sucess(sample_player, sample_game, session:Session):
    """Test de repartir mazo de reposicion"""

    RepositionDeckService(session).create_reposition_deck(sample_game.id)
    sample_game.players.append(sample_player)
    RepositionDeckService(session).draw_reposition_deck(sample_game.id)

    assert len(sample_player.cards) == 6
    check_instant = False
    i=0
    while i<6 and not check_instant:
        check_instant= (sample_player.cards[i].type == "instant")
        i = i+1
    assert check_instant
    assert sample_game.discard_deck is not None
    assert len(sample_game.discard_deck.cards) == 1
    assert sample_game.draft_deck is not None
    assert len(sample_game.draft_deck.cards) == 3



