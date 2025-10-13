"""Draft Deck Models."""


from sqlalchemy import Integer, Table, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from App.models.db import Base
from App.card.models import Card


draft_cards_association = Table(
        "draft_cards_association",
        Base.metadata,
        Column("draft_deck_id", ForeignKey("draft_deck.id"), primary_key=True),
        Column("card_id", ForeignKey("cards.id"), primary_key=True),
        extend_existing=True
)

class DraftDeck(Base):
    """
    Represent a draft deck

    """

    __tablename__ = 'draft_deck'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cards: Mapped[List[Card]] = relationship("Card",
                                             secondary="draft_cards_association",
                                             backref="draft_deck")
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey('games.id'), unique=True, nullable = True)
    
    game: Mapped["Game"] = relationship( # type: ignore
        "Game",
        back_populates="draft_deck",
        uselist=False
    )
    number_of_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)