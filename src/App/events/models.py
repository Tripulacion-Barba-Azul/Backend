"""Game's Events Models."""

from sqlalchemy import (
    Column, Table, Integer,Boolean, String, ForeignKey, Enum as SqlEnum
    )
from sqlalchemy.orm import Mapped, mapped_column, relationship
from App.models.db import Base
from App.events.enums import Direction, EventType
from App.players.models import Player
from App.card.models import Card
from App.sets.models import DetectiveSet

class Event(Base):
    """
        Represents an event in an active game
    """

    __tablename__ = 'events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"))
    
    type: Mapped[EventType] = mapped_column(
        SqlEnum(EventType),
        nullable=False
    )
    main_player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    selected_player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    played_card_id: Mapped[int] = mapped_column(Integer,ForeignKey("cards.id"), nullable=True)
    dset_id: Mapped[int] = mapped_column(Integer, ForeignKey("detective_sets.id"), nullable=True)
    cancelable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    direction: Mapped[Direction] = mapped_column(SqlEnum(Direction), nullable=True)

    game: Mapped["Game"] = relationship("Game", back_populates="events")
    main_player: Mapped[Player] = relationship('Player', foreign_keys=[main_player_id]) # quien inicia el evento
    selected_player: Mapped[Player] = relationship('Player', foreign_keys=[selected_player_id]) # actor secundario del evento
    played_card: Mapped[Card] = relationship('Card', foreign_keys=[played_card_id])
    dset: Mapped[DetectiveSet] = relationship('DetectiveSet', foreign_keys=[dset_id])
