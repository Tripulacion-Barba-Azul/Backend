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
        Column("discard_deck_id", ForeignKey("discard_deck.id"), primary_key=True),
        Column("card_id", ForeignKey("cards.id"), primary_key=True),
        extend_existing=True
)

class DiscardDeck(Base):
    """
    Represent a discard deck

    """

    __tablename__ = 'discard_deck'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cards: Mapped[List[Card]] = relationship("Card",
                                             secondary="discard_cards_association",
                                             backref="discard_deck")
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey('games.id'), unique=True, nullable = True)
    
    game: Mapped["Game"] = relationship( # type: ignore
        "Game",
        back_populates="discard_deck",
        uselist=False
    )