"""Card Models."""

from sqlalchemy import Column, Integer, String, Table, ForeignKey, Boolean
from sqlalchemy.orm import relationship, mapped_column
from typing import List
from sqlalchemy.orm import Mapped
from App.models.db import Base
from App.players.models import Player


card__player = Table(
     "card_player_association",
     Base.metadata,
     Column("card_id", ForeignKey("card.id"), primary_key=True),
     Column("player_id", ForeignKey("player.id"), primary_key=True),
)


class Card(Base):
    """
    Represent a Card

    """

    __tablename__ = "cards"

    id: Mapped [int] = mapped_column (Integer, primary_key=True, autoincrement=True)
    name = Column (String, nullable=False)
    effect = Column(String, nullable=False)
    subclass: Mapped[str] = mapped_column(String, nullable=False)


    __mapper_args__ = {
        "polymorphic_on": subclass,            # columna de subclase
        "polymorphic_identity": "carta",   # identidad de la clase base
    }


class Devious(Card):
    """
    Represent a Devious Card

    """

    __tablename__ = "devious"

    id: Mapped[int] = mapped_column(ForeignKey("cartas.id"), primary_key=True)
    playable_on_turn: Mapped[bool] = mapped_column(Boolean, nullable=False)
    

    __mapper_args__ = {
        "polymorphic_identity": "devious",
    }


class Detective(Card):
    """
    Represent a Detective Card

    """


    __tablename__ = "detectives"

    id: Mapped[int] = mapped_column(ForeignKey("cartas.id"), primary_key=True)
    number_to_set: Mapped[int] = mapped_column(Integer, nullable=False)
    playable_on_turn: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "detective",
    }


class Event(Card):
    """
    Represent a Event Card

    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(ForeignKey("cartas.id"), primary_key=True)
    playable_on_turn: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "event",
    }


class Instant(Card):

    """
    Represent a Instant Card

    """
    __tablename__ = "instants"

    id: Mapped[int] = mapped_column(ForeignKey("cartas.id"), primary_key=True)
    playable: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "instant",
    }