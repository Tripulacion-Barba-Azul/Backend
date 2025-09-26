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
