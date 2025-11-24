from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.App.models.db import Base, engine
from src.api import api_router
from src.App.websockets import websocket_router

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)

# Connecting to DB and creating tables
Base.metadata.create_all(engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}


# Including routers
app.include_router(api_router)
app.include_router(websocket_router)
