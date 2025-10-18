"""Games Models."""

from sqlalchemy import (
    Column, Table, Integer, String, ForeignKey, Enum as SqlEnum
    )
from sqlalchemy.orm import Mapped, relationship, mapped_column
from App.decks.discard_deck_model import DiscardDeck
from App.decks.draft_deck_model import DraftDeck
from App.models.db import Base
from App.games.enums import ActionStatus, GameStatus, Winners
from App.players.models import Player
from App.decks.reposition_deck_model import RepositionDeck


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
    action_status: Mapped[ActionStatus] = mapped_column(
            SqlEnum(ActionStatus),
            default=ActionStatus.BLOCKED,
            nullable=False
    )
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey('players.id'), nullable=False)
    min_players: Mapped[int] = mapped_column(Integer, nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    num_players: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    owner: Mapped[Player] = relationship(Player, foreign_keys=[owner_id])
    players: Mapped[list[Player]] = relationship(
        Player,
        secondary="game_players_association",
        backref=None
    )
    winners: Mapped[Winners | None] = mapped_column(
        SqlEnum(Winners),
        default=None,
        nullable=True
    )

    reposition_deck: Mapped[RepositionDeck] = relationship(
        "RepositionDeck",
        back_populates="game", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    discard_deck: Mapped[DiscardDeck] = relationship(
        "DiscardDeck",
        back_populates="game", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    draft_deck: Mapped[DraftDeck] = relationship(  
        "DraftDeck",        
        back_populates="game",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __init__(self, 
                 name: str, 
                 min_players: int, 
                 max_players: int, 
                 owner: Player
    ):
        self.name = name
        self.owner = owner
        self.min_players = min_players
        self.max_players = max_players
        self.players = [owner]
    