"""Application main module."""

from fastapi import FastAPI

from App.models.db import Base, engine

app = FastAPI()

# Connecting to DB and creating tables
Base.metadata.create_all(engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}
