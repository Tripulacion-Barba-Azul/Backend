from pydantic import BaseModel

from App.card.schemas import CardPublicInfo

class SetPublicInfo(BaseModel):
    setName: str
    cards: list[CardPublicInfo] 