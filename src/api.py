"""Defines API."""

from fastapi import APIRouter
from App.games.endpoints import games_router


api_router = APIRouter()
api_router.include_router(games_router, prefix="/games", tags=["games"])
