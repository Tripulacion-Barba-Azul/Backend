from datetime import date
from sqlalchemy.orm import Session

from App.players.dtos import PlayerDTO
from App.players.models import Player
from App.players.services import PlayerService

def test_create_player_service(session: Session):

    player_service = PlayerService(session)

    player_dto = PlayerDTO(
        name="Barba Azul",
        birthday=date(2000,1,1)
    )
    player_service.create(player_dto)

    db_player = session.query(Player).filter_by(name="Barba Azul").first()

    assert db_player is not None
    assert db_player.id is not None
    assert db_player.name == "Barba Azul"
    assert db_player.birthday == date(2000,1,1)
