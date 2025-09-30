import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import date
from App.secret.models import Secret
from App.players.models import Player
from App.secret.enums import SecretType


@pytest.fixture
def sample_player(session:Session):
    player = Player(name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player



def test_create_secret(session:Session):
    test_secret = Secret(name = "test_name",
                        description = "test_description",
                        type = SecretType.GENERIC,
                        revealed = False,
                        )
    session.add(test_secret)
    session.commit()
    session.refresh(test_secret)

    secret = session.query(Secret).filter_by(name = "test_name").first()

    assert secret is not None
    assert secret.id is not None
    assert secret.name == "test_name"
    assert secret.description == "test_description"
    assert secret.type == SecretType.GENERIC
    assert secret.revealed == False
    



def test_secret_obligatory_fields(session:Session):
    """Test que verifica que los campos requeridos sean obligatorios """
    with pytest.raises(IntegrityError):
        secret = Secret(description = "test_description",
                        type = SecretType.GENERIC,
                        revealed = False,
                        )
        session.add(secret)
        session.commit()


def test_secret_revealed(session:Session):
    """Test que verifica que los campos pueden cambiarse"""

    secret = Secret(name="test_name",
                    description="test_description",
                    type=SecretType.GENERIC,
                    revealed=False
    )
    session.add(secret)
    session.commit()
    assert secret.revealed == False
    
    secret.revealed = True
    session.commit()
    session.refresh(secret)
    
    assert secret.revealed == True


def test_secret_player_relationship(session:Session, sample_player):
    """Test que verifica la relacion entres secreto y jugador"""
    secret = Secret(
        name="relational_secret",
        description="Testing relationship",
        type=SecretType.GENERIC,
        revealed=False
    )
    
    sample_player.secrets.append(secret)
    session.add(secret)
    session.commit()
    session.refresh(sample_player)
    session.refresh(secret)
    
    assert len(secret.players) == 1
    assert secret.players[0].name == "Elias"