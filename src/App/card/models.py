"""Card Models."""

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from App.models.db import Base



class Card(Base):
    """
    Represent a Card

    """

    __tablename__ = "cards"

    id: Mapped [int] = mapped_column (Integer, primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column (String, nullable=False)
    effect: Mapped[str]  = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    playable_on_turn: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    number_to_set: Mapped[int] = mapped_column(Integer, nullable=True)
    playable: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
    order: Mapped[int] = mapped_column(Integer, nullable=True, default=0)

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