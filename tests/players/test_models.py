from datetime import date
from sqlalchemy.orm import Session

from App.players.models import Player

def test_create_player(session: Session):

    player_name = "Barba Azul"
    player_birthday = date(2000,1,1)
    player = Player(
        name = player_name,
        avatar = "", 
        birthday = player_birthday,)
    session.add(player)
    session.commit()

    db_player: Player|None= session.query(Player).filter_by(name=player_name).first()

    assert db_player is not None
    assert db_player.id is not None
    assert db_player.name == player_name
    assert db_player.avatar == ""
    assert db_player.birthday == player_birthday
