"""Players Models."""

from datetime import date
from sqlalchemy import Integer, String , Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from App.models.db import Base
from App.card.models import Card
from App.secret.models import Secret

class Player(Base):
    """
    Represent a Player

    """

    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str] = mapped_column(String)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
    cards: Mapped[List["Card"]] = relationship(back_populates="players")
    secrets: Mapped[List["Secret"]] = relationship(back_populates="players")

