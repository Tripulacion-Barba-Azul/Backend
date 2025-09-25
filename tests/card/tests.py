import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import date
from ....Backend.src.App.card.models import Card, Devious, Event, Detective, Instant
from ....Backend.src.App.players.models import Player


@pytest.fixture
def sample_player(session:Session):
    player = Player(id=1, name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    return player



def test_card_obligatory_fields(session:Session):
    """Test que verifica que los campos requeridos sean obligatorios """
    with pytest.raises(IntegrityError):
        card = Card(effect = "test_effect",
                    type = "test",
                    player_id = sample_player().id
                    )
        session.add(card)
        session.commit()
    

def test_card_optional_fields(session:Session):
    """Test que verifica que los campos opcionales funcionen correctamente"""
    card = Card(
        name="Test Card",
        effect="Test Effect",
        type="carta",
        player_id=sample_player().id
        
    )
    
    session.add(card)
    session.commit()
    
    assert card.playable_on_turn is None
    assert card.number_to_set is None
    assert card.playable is None



def test_create_devious_card(session:Session):
    
    #creamos la carta

    devious_card = Devious(name = "test_devious",
                        effect = "test_effect",
                        type = "devious",
                        player_id = sample_player().id)
    session.add(devious_card)
    session.commit()

    card = session.query(Card).filter_by(name = "test_devious").first
    assert card is not None
    assert card.type == "devious"
    assert isinstance(card, Card)
    assert isinstance(card, Devious)
    assert card.polymorphic_identity == "devious"


def test_create_detective_card(session:Session):
    
    #creamos la carta

    detective_card = Detective(name = "test_detective",
                        effect = "test_effect",
                        type = "detective",
                        player_id = sample_player().id)
    session.add(detective_card)
    session.commit()

    card = session.query(Card).filter_by(name = "test_detective").first
    assert card is not None
    assert card.type == "detective"
    assert isinstance(card, Card)
    assert isinstance(card, Detective)
    assert card.polymorphic_identity == "detective"


def test_create_instant_card(session:Session):
    

    #creamos la carta

    instant_card = Instant(name = "test_instant",
                        effect = "test_effect",
                        type = "instant",
                        player_id = sample_player().id)
    session.add(instant_card)
    session.commit()

    card = session.query(Card).filter_by(name = "test_instant").first
    assert card is not None
    assert card.type == "instant"
    assert isinstance(card, Card)
    assert isinstance(card, Instant)
    assert card.polymorphic_identity == "instant"


def test_create_event_card(session:Session):


    #creamos la carta

    event_card = Event(name = "test_event",
                        effect = "test_effect",
                        type = "event",
                        player_id = sample_player().id)
    session.add(event_card)
    session.commit()

    card = session.query(Card).filter_by(name = "test_event").first
    assert card is not None
    assert card.type == "event"
    assert isinstance(card, Card)
    assert isinstance(card, Event)
    assert card.polymorphic_identity == "event"




def test_card_player_relationship(session:Session):
    """Test de la relación con Player"""
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "card",
        player_id = sample_player().id
    )
    
    session.add(card)
    session.commit()
    
    # verifica la relación directa
    assert card.player_id == sample_player().id
    assert card.player.name == "Elias"
    
    # verifica la relación inversa
    assert len(sample_player.cards) == 1
    assert sample_player.cards[0].name == "test_card"
