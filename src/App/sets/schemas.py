from pydantic import BaseModel

from App.card.dtos import CardPublicInfo

class SetPublicInfo(BaseModel):
    setName: str
    cards: list[CardPublicInfo] 