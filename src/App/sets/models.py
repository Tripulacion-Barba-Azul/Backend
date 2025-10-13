"""Detective Sets Models."""

from sqlalchemy import (Integer, Table, ForeignKey, 
        Column, Enum as SqlEnum)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from App.card.models import Card


from App.sets.enums import DetectiveSetType
from App.models.db import Base

set_cards_association = Table(
        "set_cards_association",
        Base.metadata,
        Column("set_id", ForeignKey("detective_sets.id"), primary_key=True),
        Column("card_id", ForeignKey("cards.id"), primary_key=True),
)

class DetectiveSet(Base):
    """
    Represent a Detective Set

    """

    __tablename__ = "detective_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[DetectiveSetType] = mapped_column(
        SqlEnum(DetectiveSetType),
        nullable=False
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    player: Mapped["Player"] = relationship("Player", back_populates="sets")
    cards: Mapped[list[Card]] = relationship(
        "Card",
        secondary="set_cards_association",
        backref="detective_sets"
    )


