"""Players Models."""

from datetime import date
from sqlalchemy import Integer, String , Date
from sqlalchemy.orm import Mapped, mapped_column
from App.models.db import Base


class Player(Base):
    """
    Represent a Player

    """

    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str] = mapped_column(String)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
