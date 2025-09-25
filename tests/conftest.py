import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from App.models.db import Base



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