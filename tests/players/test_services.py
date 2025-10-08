from datetime import date
from fastapi.testclient import TestClient
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


def test_discard_card_service(session: Session, seed_game_player2_discard):

    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]

    card = player.cards[2]

    discarded_card = PlayerService(session).discard_card(player.id, card)    

    assert discarded_card.id == card.id
    assert discarded_card not in player.cards