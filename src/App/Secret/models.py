"""Secret Models."""

from sqlalchemy import Column, Integer, String, Table, ForeignKey, Boolean
from sqlalchemy.orm import relationship, mapped_column
from typing import List
from sqlalchemy.orm import Mapped
from App.models.db import Base
from App.players.models import Player


secret_player = Table(
     "secret_player_association",
     Base.metadata,
     Column("secret_id", ForeignKey("secret.id"), primary_key=True),
     Column("player_id", ForeignKey("player.id"), primary_key=True),
)


class Card(Base):
    """
    Represent a Secret

    """

    __tablename__ = "secret"

    id: Mapped [int] = mapped_column (Integer, primary_key=True, autoincrement=True)
    name = Column (String, nullable=False)
    description = Column(String, nullable=False)
    assassin = Column(Boolean, nullable=False)
    acomplice = Column(Boolean, nullable=False)
    