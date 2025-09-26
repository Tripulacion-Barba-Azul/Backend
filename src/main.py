"""Application main module."""

from fastapi import FastAPI

from App.models.db import Base, engine
from App.websockets import websocket_router

app = FastAPI()

# Connecting to DB and creating tables
Base.metadata.create_all(engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}

app.include_router(websocket_router)