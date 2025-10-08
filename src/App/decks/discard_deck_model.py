"""Discard Deck Models."""

from datetime import date
from sqlalchemy import Integer, Table, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from App.models.db import Base
from App.card.models import Card


discard_cards_association = Table(
        "discard_cards_association",
        Base.metadata,
        Column("reposition_deck_id", ForeignKey("reposition_deck.id"), primary_key=True),
        Column("card_id", ForeignKey("cards.id"), primary_key=True),
        Column("order", autoincrement=True),
        extend_existing=True
)

class DiscardDeck(Base):
    """
    Represent a discard deck

    """

    __tablename__ = 'discard_deck'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cards: Mapped[List[Card]] = relationship("Card",
                                             secondary="reposition_cards_association",
                                             backref="reposition_deck")
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey('games.id'), unique=True, nullable = True)
    
    game: Mapped["Game"] = relationship(
        "Game",
        back_populates="reposition_deck",
        uselist=False
    )