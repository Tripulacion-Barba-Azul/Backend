"""Secret Models."""

from sqlalchemy import  Integer, String, Enum as SqlEnum, Boolean
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from App.models.db import Base
from App.secret.enums import SecretType




class Secret(Base):
    """
    Represent a Secret

    """

    __tablename__ = "secrets"

    id: Mapped [int] = mapped_column (Integer, primary_key=True, autoincrement=True)
    name: Mapped[str]  = mapped_column (String, nullable=False)
    description: Mapped[str]  = mapped_column(String, nullable=False)
    type: Mapped [SecretType] =mapped_column(SqlEnum(SecretType),
                                            default=SecretType.GENERIC, 
                                            nullable=False)
    revealed: Mapped[bool] = mapped_column(Boolean, nullable=False)

