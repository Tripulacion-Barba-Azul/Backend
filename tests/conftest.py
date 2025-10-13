from datetime import date
from App.games.models import Game
from App.players.models import Player
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from App.models.db import Base, get_db
from App.games.dtos import GameDTO
from App.games.services import GameService
from App.players.dtos import PlayerDTO
from main import app

from .game_fixtures import *


@pytest.fixture(name="sample_player")
def sample_player_fixture(session: Session):
    """Fixture global para crear un player de prueba accesible por otros fixtures/tests"""
    from App.players.models import Player

    player = Player(name="Elias", avatar=1, birthday=date(1999, 3, 13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture(name="session", scope="function")
def session_fixture():
    
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={
            "check_same_thread": False
        },
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(name="client")
def client_fixture(session: Session):  
    def get_db_override():  
        return session

    app.dependency_overrides[get_db] = get_db_override  

    client = TestClient(app)  
    yield client  
    app.dependency_overrides.clear()


@pytest.fixture(name="seed_games")
def seed_games_fixture(session: Session):
    player1 = Player(name = "Barba Azul", avatar = 1, birthday = date(2000,1,1))
    game1 = Game(
        name = "Tripulación de Barba Azul",
        min_players = 2,
        max_players = 4,
        owner = player1,
    )

    player2 = Player(name = "Barba Negra", avatar = 2, birthday = date(2000,1,1))
    game2 = Game(
        name = "Tripulación de Barba Negra",
        min_players = 2,
        max_players = 4,
        owner = player2,
    )

    session.add_all([game1, game2])
    session.commit()

    return {"players": [player1, player2], "games": [game1, game2]}


@pytest.fixture(name="sample_game")
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