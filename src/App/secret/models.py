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
    name: Mapped[str]  = mapped_column (String, nullable=False)
    description: Mapped[str]  = mapped_column(String, nullable=False)
    assassin: Mapped[bool] = mapped_column(Boolean, nullable=False)
    acomplice: Mapped[bool] = mapped_column(Boolean, nullable=False)
    revealed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey('players.id'), nullable=True) 
    player: Mapped["Player"] = relationship(back_populates="secrets")
    