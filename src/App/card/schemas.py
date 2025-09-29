from pydantic import BaseModel

class CardGameInfo(BaseModel):
    cardOwnerID: int
    cardID: int
    cardName: str
    