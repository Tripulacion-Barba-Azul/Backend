from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from App.players.dtos import PlayerDTO
from App.players.models import Player
from App.players.services import PlayerService
from App.players.enums import PlayerRole
from App.secret.enums import SecretType

def test_create_player_service(session: Session):

    player_service = PlayerService(session)

    player_dto = PlayerDTO(
        name="Barba Azul",
        avatar=1,
        birthday=date(2000,1,1)
    )
    player_service.create(player_dto)

    db_player = session.query(Player).filter_by(name="Barba Azul").first()

    assert db_player is not None
    assert db_player.id is not None
    assert db_player.name == "Barba Azul"
    assert db_player.avatar == 1
    assert db_player.birthday == date(2000,1,1)


def test_discard_card_service(session: Session, seed_game_player2_discard):

    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]

    card = player.cards[2]

    discarded_card = PlayerService(session).discard_card(player.id, card)    

    assert discarded_card.id == card.id
    assert discarded_card not in player.cards


def test_set_social_disgrace_player(session: Session, seed_started_game):
    game = seed_started_game(2)

    player = game.players[0]
    assert not player.in_social_disgrace
    PlayerService(session).set_social_disgrace(player)
    assert not player.in_social_disgrace

    for secret in player.secrets:
        secret.revealed = True

    PlayerService(session).set_social_disgrace(player)
    assert player.in_social_disgrace

def test_set_social_disgrace_accomplice(session: Session, seed_started_game):
    game = seed_started_game(5)

    accomplice = next(player for player in game.players if player.role == PlayerRole.ACCOMPLICE)
    accomplice_secret =  next(secret for secret in accomplice.secrets if secret.type == SecretType.ACCOMPLICE)
    accomplice_secret.revealed = True

    assert not accomplice.in_social_disgrace
    PlayerService(session).set_social_disgrace(accomplice)
    assert accomplice.in_social_disgrace

    accomplice_secret.revealed = False
    assert accomplice.in_social_disgrace
    PlayerService(session).set_social_disgrace(accomplice)
    assert not accomplice.in_social_disgrace

   
    
