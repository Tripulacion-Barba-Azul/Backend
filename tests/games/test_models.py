from datetime import date
from sqlalchemy.orm import Session

from App.games.models import Game
from App.games.enums import GameStatus
from App.players.models import Player

def test_create_game(session: Session):

    player = Player(name = "Barba Azul", avatar = "", birthday = date(2000,1,1))

    game_name = "Tripulación de Barba Azul"
    game = Game(
        name = game_name,
        min_players = 2,
        max_players = 4,
        owner = player,
    )

    session.add(game)
    session.commit()

    db_player = session.query(Player).filter_by(name="Barba Azul").first()
    db_game = session.query(Game).filter_by(name=game_name).first()

    assert db_player is not None
    assert db_game is not None

    assert db_game.id is not None
    assert db_game.name == game_name
    assert db_game.status == GameStatus.WAITING
    assert db_game.min_players == 2
    assert db_game.max_players == 4
    assert db_game.num_players == 1
    assert db_game.turn_number == 0
    assert db_game.owner_id == db_player.id
    assert db_game.owner == db_player
    assert db_game.players == [db_player]
