"""Secret Models."""

from sqlalchemy import Column, Integer, String, Table, ForeignKey, Boolean
from sqlalchemy.orm import relationship, mapped_column
from typing import List
from sqlalchemy.orm import Mapped
from App.models.db import Base
from App.players.models import Player




class Card(Base):
    """
    Represent a Secret

    """

    __tablename__ = "secrets"

    id: Mapped [int] = mapped_column (Integer, primary_key=True, autoincrement=True)
    name = Column (String, nullable=False)
    description = Column(String, nullable=False)
    assassin = Column(Boolean, nullable=False)
    acomplice = Column(Boolean, nullable=False)
    playerId: Mapped[int] = mapped_column(Integer, ForeignKey('players.id')) 
    player: Mapped["Player"] = relationship(back_populates="secrets")
    