import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import date
from ....Backend.src.App.secret.models import Secret
from ....Backend.src.App.players.models import Player


@pytest.fixture
def sample_player(session:Session):
    player = Player(id=1, name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    return player



def test_create_secret(session:Session):
    test_secret = Secret(name = "test_name",
                        description = "test_description",
                        assassin = False,
                        acomplice = True,
                        revealed = False,
                        player_id = sample_player().id
                        )
    session.add(test_secret)
    session.commit()

    secret = session.query(Secret).filter_by(name = "test_secret").first

    assert secret is not None
    assert secret.id is not None
    assert secret.name == "test_name"
    assert secret.description == "test_description"
    assert secret.assassin == False
    assert secret.acomplice == True
    assert secret.revealed == False
    assert secret.player_id == sample_player().id



def test_secret_obligatory_fields(session:Session):
    """Test que verifica que los campos requeridos sean obligatorios """
    with pytest.raises(IntegrityError):
        secret = Secret(description = "test_description",
                    assassin = False,
                    acomplice = False,
                    revealed = False,
                    player_id = sample_player().id
                    )
        session.add(secret)
        session.commit()



def test_secret_player_relationship(session:Session):
    """Test de la relación con Player"""
    secret = Secret(
        name = "test_secret",
        description = "test_description",
        assassin = False,
        player_id = sample_player().id
    )
    
    session.add(secret)
    session.commit()
    
    # verifica la relación directa
    assert secret.player_id == sample_player().id
    assert secret.player.name == "test_secret"
    
    # verifica la relación inversa
    assert len(sample_player.secrets) == 1
    assert sample_player.secrets[0].name == "test_card"

 
        