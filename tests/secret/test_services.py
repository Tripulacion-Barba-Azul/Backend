import pytest

from sqlalchemy.orm import Session
from App.secret.models import Secret
from App.secret.services import *
from App.games.models import Game
from App.players.models import Player
from datetime import date
from App.secret.enums import SecretType

@pytest.fixture
def sample_secret(session:Session):
    new_name = "test_secret"
    new_description = "test_description"
    new_type = SecretType.GENERIC

    secret = create_secret(new_name, new_description, new_type)
    return secret



@pytest.fixture
def sample_player(session:Session):
    player = Player(name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture
def sample_player1(session:Session):
    player = Player(name="Eliseo", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture
def sample_player2(session:Session):
    player = Player(name="Joaquin", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture
def sample_player3(session:Session):
    player = Player(name="Marcos", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture
def sample_player4(session:Session):
    player = Player(name="Santiago", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture
def sample_player5(session:Session):
    player = Player(name="Tomas", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
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
def sample_game_with_players(session,
                            sample_player,
                            sample_player1,
                            sample_player2,
                            sample_player3,
                            sample_player4,
                            sample_player5):
    """Fixture para crear un game de prueba"""
    game = Game(
        name="test_game",
        min_players=2,
        max_players=4,
        owner= sample_player
    )
    session.add(game)
    game.players.append(sample_player1)
    game.players.append(sample_player2)
    game.players.append(sample_player3)
    game.players.append(sample_player4)
    game.players.append(sample_player5)

    session.commit()
    session.refresh(game)
    for player in game.players:
        session.refresh(player)
    return game


def test_get_secret_success(session:Session):
    """Test para obtener un secreto segun su id"""
    new_secret = Secret(
        name="test_secret",
        description = "test_description",
        type = SecretType.GENERIC,
        revealed = False
    )
    session.add(new_secret)
    session.commit()
    session.refresh(new_secret)

    getted_secret = get_secret(new_secret.id, session)

    assert getted_secret.name == new_secret.name
    assert getted_secret.description == new_secret.description
    assert getted_secret.type == new_secret.type


def test_get_secret_unsucces(session:Session):
    """Test que al intentar obtener un secreto inexistente lanza error"""
    with pytest.raises(ValueError, match="Secret with id:999 dont exist"):
            get_secret(999, session)
    

def test_create_secret(session:Session):
    new_name = "test_secret"
    new_description = "test_description"
    new_type = SecretType.GENERIC

    secret = create_secret(new_name, new_description, new_type)

    session.add(secret)
    session.commit()
    session.refresh(secret)

    assert secret.name == new_name
    assert secret.description == new_description
    assert secret.type == new_type

def test_reveal_secret(sample_secret ,session:Session):
    secret = sample_secret
    session.add(secret)
    session.commit()
    session.refresh(secret)

    reveal_secret(secret, session)

    assert secret.revealed == True


def test_relate_secret_player(sample_secret, sample_player, session:Session):
    relate_secret_player(sample_player, sample_secret, session)

    assert len(sample_secret.players) == 1
    assert sample_secret.players[0].name == "Elias"

def test_create_and_draw_secrets(sample_game,sample_game_with_players, session:Session):

    create_and_draw_secrets(sample_game.id, session)
    player = sample_game.players[0]
    player_secrets = player.secrets

    assert len(player_secrets) == 3
    assert (player_secrets[0].type or player_secrets[1].type or player_secrets[2].type == SecretType.ASSASSIN)
    player.secrets = []

    create_and_draw_secrets(sample_game_with_players.id, session)
    player1 = sample_game_with_players.players[0]
    player1_secrets = player1.secrets

    assert len(player1_secrets) == 3
    i=0
    check_assasin = False
    while i < 6 and not check_assasin:
        sample_game_with_players.players[i] = player
        check_assasin = player_secrets[0].type or player_secrets[1].type or player_secrets[2].type == SecretType.ASSASSIN
    
    assert check_assasin
    i=0
    check_accomplice = False

    while i < 6 and not check_accomplice:
        sample_game_with_players.players[i] = player
        check_accomplice = player_secrets[0].type or player_secrets[1].type or player_secrets[2].type == SecretType.ACCOMPLICE
    
    assert check_accomplice