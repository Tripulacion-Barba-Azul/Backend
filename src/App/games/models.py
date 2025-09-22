"""Games Models."""

from sqlalchemy import (
    Column, Table, Integer, String, ForeignKey, Enum as SqlEnum
    )
from sqlalchemy.orm import Mapped, relationship, mapped_column
from App.models.db import Base
from App.games.enums import GameStatus
from App.players.models import Player


game_players_association = Table(
        "game_players_association",
        Base.metadata,
        Column("game_id", ForeignKey("games.id"), primary_key=True),
        Column("player_id", ForeignKey("players.id"), primary_key=True),
)

class Game(Base):
    """
    Represent a Game

    """

    __tablename__ = 'games'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[GameStatus] = mapped_column(
            SqlEnum(GameStatus), 
            default=GameStatus.WAITING,
            nullable=False
    )
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey('players.id'), nullable=False)
    min_players: Mapped[int] = mapped_column(Integer, nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    num_players: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    players_order: Mapped[str] = mapped_column(String, default="", nullable=False) # order of players.id as String

    owner: Mapped[Player] = relationship(Player, foreign_keys=[owner_id])
    players: Mapped[list[Player]] = relationship(
        Player,
        secondary="game_players_association",
        backref=None
    )
