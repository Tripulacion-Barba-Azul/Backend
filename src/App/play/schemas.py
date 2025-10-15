from pydantic import BaseModel

from App.card.schemas import CardGameInfo
from App.players.schemas import PlayerGameInfo
from App.card.schemas import CardGameInfo
    
class PlayCardInfo(BaseModel):
    event: str = "play_card"
    players: list[PlayerGameInfo]
    cards: list[CardGameInfo]
    
class PlayCard(BaseModel):
    playerId: int
    cards: list[int]

class DrawCardInfo(BaseModel):
    playerId: int

class StealSetInfo(BaseModel):
    playerId: int
    stolenPlayerId: int
    setId: int

class NotifierStealSet(BaseModel):
    event: str =  "notifierStealSet"
    payload: StealSetInfo