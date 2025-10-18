from datetime import date
from sqlalchemy.orm import Session

from App.games.dtos import GameDTO
from App.games.enums import GameStatus
from App.games.models import Game
from App.games.services import GameService
from App.players.dtos import PlayerDTO
from App.players.models import Player
from App.players.services import PlayerService


def test_create_game_service(session: Session):

    game_service = GameService(session)

    player_dto = PlayerDTO(
        name="Barba Azul",
        avatar=1,
        birthday=date(2000,1,1)
    )

    game_dto = GameDTO(
        name="Tripulación de Barba Azul",
        min_players = 2,
        max_players = 4,
    )

    game_service.create(
        player_dto=player_dto,
        game_dto=game_dto
    )

    db_player = session.query(Player).filter_by(name="Barba Azul").first()
    db_game = session.query(Game).filter_by(name="Tripulación de Barba Azul").first()

    assert db_player is not None
    assert db_game is not None

    assert db_game.id is not None
    assert db_game.name == "Tripulación de Barba Azul"
    assert db_game.status == GameStatus.WAITING
    assert db_game.min_players == 2
    assert db_game.max_players == 4
    assert db_game.num_players == 1
    assert db_game.turn_number == 0
    assert db_game.owner_id == db_player.id
    assert db_game.owner == db_player
    assert db_game.players == [db_player]


def test_exit_game_service(session: Session, seed_games):

    game = seed_games["games"][0]
    

    player_dto = PlayerDTO(
        name="sample_player",
        avatar="asdas",
        birthday=date(2000,1,1)
    )
    
    owner_id = game.owner_id

    GameService(session).join(
        game_id=game.id,
        player_dto=player_dto
    )

    session.commit()
    session.refresh(game)
    player = session.query(Player).filter_by(name="sample_player").first()

    GameService(session).exit_game_service(game.id, player.id)

    db_game = session.query(Game).filter_by(id=game.id).first()
    db_player: Player | None = session.query(Player).filter_by(id=player.id).first()

    assert db_game is not None
    assert db_player is None
    assert db_game.num_players == 1
    assert db_game.owner_id == owner_id
   