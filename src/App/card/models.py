"""Card Models."""

from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy.orm import Mapped
from App.models.db import Base
from App.players.models import Player


class Card(Base):
    """
    Represent a Card

    """

    __tablename__ = "cards"

    id: Mapped [int] = mapped_column (Integer, primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column (String, nullable=False)
    effect: Mapped[str]  = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    playable_on_turn: Mapped[bool] = mapped_column(Boolean, nullable=True)
    number_to_set: Mapped[int] = mapped_column(Integer, nullable=True)
    playable: Mapped[bool] = mapped_column(Boolean, nullable=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey('players.id'), nullable=True) 
    player: Mapped["Player"] = relationship(back_populates="cards")


    __mapper_args__ = {
        "polymorphic_on": type,            # usa la columna type para definir la subclase
        "polymorphic_identity": "carta",   # identidad de la clase base
    }


class Devious(Card):
    """
    Represent a Devious Card

    """

    __mapper_args__ = {
        "polymorphic_identity": "devious",
    }


class Detective(Card):
    """
    Represent a Detective Card

    """

    __mapper_args__ = {
        "polymorphic_identity": "detective",
    }


class Event(Card):
    """
    Represent a Event Card

    """

    __mapper_args__ = {
        "polymorphic_identity": "event",
    }


class Instant(Card):

    """
    Represent a Instant Card

    """

    __mapper_args__ = {
        "polymorphic_identity": "instant",
    }