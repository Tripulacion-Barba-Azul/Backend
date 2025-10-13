import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import date
from App.card.models import Card, Devious, Event, Detective, Instant
from App.players.models import Player


@pytest.fixture
def sample_player(session:Session):
    player = Player(name="Elias",
                    avatar="kjhgdsFAKJHG",
                    birthday= date(1999,3,13)
                    )
    
    session.add(player)
    session.commit()
    session.refresh(player)

    return player



def test_card_obligatory_fields(session:Session):
    """Test que verifica que los campos requeridos sean obligatorios """
    with pytest.raises(IntegrityError):
        card = Card(effect = "test_effect",
                    type = "test"
                    )
        session.add(card)
        session.commit()
    

def test_card_optional_fields(session:Session):
    """Test que verifica que los campos opcionales funcionen correctamente"""
    card = Card(name="Test Card",
                effect="Test Effect",
                type="carta"
                )
    
    session.add(card)
    session.commit()
    session.refresh(card)

    assert card.playable_on_turn is False
    assert card.number_to_set is None
    assert card.playable is True



def test_create_devious_card(session:Session):
    
    devious_card = Devious(name = "test_devious",
                            effect = "test_effect",
                            type = "devious"
                            )
    session.add(devious_card)
    session.commit()
    session.refresh(devious_card)

    card = session.query(Card).filter_by(name = "test_devious").first()
    assert card is not None
    assert card.type == "devious"
    assert isinstance(card, Card)
    assert isinstance(card, Devious)



def test_create_detective_card(session:Session):
    
    detective_card = Detective(name = "test_detective",
                                effect = "test_effect",
                                type="detective"
                                )
    
    session.add(detective_card)
    session.commit()
    session.refresh(detective_card)

    card = session.query(Card).filter_by(name = "test_detective").first()
    assert card is not None
    assert card.type == "detective"
    assert isinstance(card, Card)
    assert isinstance(card, Detective)



def test_create_instant_card(session:Session):
    
    instant_card = Instant(name = "test_instant",
                            effect = "test_effect",
                            type = "instant"
                            )
    
    session.add(instant_card)
    session.commit()
    session.refresh(instant_card)

    card = session.query(Card).filter_by(name = "test_instant").first()
    assert card is not None
    assert card.type == "instant"
    assert isinstance(card, Card)
    assert isinstance(card, Instant)
    


def test_create_event_card(session:Session):

    event_card = Event(name = "test_event",
                        effect = "test_effect",
                        type = "event"
                        )
    session.add(event_card)
    session.commit()
    session.refresh(event_card)

    card = session.query(Card).filter_by(name = "test_event").first()
    assert card is not None
    assert card.type == "event"
    assert isinstance(card, Card)
    assert isinstance(card, Event)




def test_card_player_relationship(session:Session, sample_player):
    """Test de la relación con Player"""
    card = Card(
        name = "test_Card",
        effect = "test_effect",
        type = "card"
    )
    
    sample_player.cards.append(card)
    session.add(card)
    session.commit()
    session.refresh(sample_player)
    session.refresh(card)

   
    assert len(card.players) == 1
    assert card.players[0].name == "Elias"
