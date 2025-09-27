from datetime import date
from App.games.models import Game
from App.players.models import Player
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from App.models.db import Base, get_db
from main import app

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
    player1 = Player(name = "Barba Azul", avatar = "", birthday = date(2000,1,1))
    game1 = Game(
        name = "Tripulación de Barba Azul",
        min_players = 2,
        max_players = 4,
        owner = player1,
    )

    player2 = Player(name = "Barba Negra", avatar = "", birthday = date(2000,1,1))
    game2 = Game(
        name = "Tripulación de Barba Negra",
        min_players = 2,
        max_players = 4,
        owner = player2,
    )

    session.add_all([game1, game2])
    session.commit()

    return {"players": [player1, player2], "games": [game1, game2]}
