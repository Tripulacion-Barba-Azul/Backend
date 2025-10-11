"""Reposition Deck Models."""

from sqlalchemy import Integer, Table, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from App.models.db import Base
from App.card.models import Card


reposition_cards_association = Table(
        "reposition_cards_association",
        Base.metadata,
        Column("reposition_deck_id", ForeignKey("reposition_deck.id"), primary_key=True),
        Column("card_id", ForeignKey("cards.id"), primary_key=True),
        extend_existing=True
)

class RepositionDeck(Base):
    """
    Represent a reposition deck

    """

    __tablename__ = 'reposition_deck'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cards: Mapped[list[Card]] = relationship("Card",
                                             secondary="reposition_cards_association",
                                             backref="reposition_deck")
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey('games.id'), unique=True, nullable = True)
    
    game: Mapped["Game"] = relationship( # type: ignore
        "Game",
        back_populates="reposition_deck",
        uselist=False
    )
    number_of_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)