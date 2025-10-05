"""Defines API."""

from fastapi import APIRouter
from App.games.endpoints import games_router
from App.rounds.endpoints import rounds_router


api_router = APIRouter()
api_router.include_router(games_router, prefix="/games", tags=["games"])
api_router.include_router(rounds_router, prefix="/rounds", tags=["rounds"])
