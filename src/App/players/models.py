"""Players Models."""

from datetime import date
from sqlalchemy import (Integer, Table, String , Date, ForeignKey, 
        Column, Enum as SqlEnum)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from App.models.db import Base
from App.card.models import Card
from App.players.enums import PlayerRole, TurnStatus
from App.secret.models import Secret
from App.sets.models import DetectiveSet

player_cards_association = Table(
        "player_cards_association",
        Base.metadata,
        Column("player_id", ForeignKey("players.id"), primary_key=True),
        Column("card_id", ForeignKey("cards.id"), primary_key=True),
)

player_secrets_association = Table(
        "player_secrets_association",
        Base.metadata,
        Column("player_id", ForeignKey("players.id"), primary_key=True),
        Column("secret_id", ForeignKey("secrets.id"), primary_key=True),
)

class Player(Base):
    """
    Represent a Player

    """

    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
    turn_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[PlayerRole] = mapped_column(
        SqlEnum(PlayerRole), 
            default=PlayerRole.DETECTIVE,
            nullable=False
    )
    cards: Mapped[List[Card]] = relationship("Card",
                                             secondary="player_cards_association",
                                             backref="players")
    secrets: Mapped[List[Secret]] = relationship("Secret",
                                             secondary="player_secrets_association",
                                             backref="players")
    turn_status: Mapped[TurnStatus] = mapped_column(
        SqlEnum(TurnStatus),
        default=TurnStatus.WAITING,
        nullable=False
    )
    ally: Mapped[int] = mapped_column(Integer, ForeignKey('players.id'), nullable=True)
    sets: Mapped[list[DetectiveSet]] = relationship(
        "DetectiveSet",
        back_populates="player"
    )

