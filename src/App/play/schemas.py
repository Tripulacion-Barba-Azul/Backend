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
    
class SelectAnyPlayerInfo(BaseModel):
    playerId: int
    selectedPlayerId: int
    
class CardsOffTheTableInfo(BaseModel):
    playerId: int
    quantity: int
    selectedPlayerId: int
    
class NotifierCardsOffTheTable(BaseModel):
    event: str = "notifierCardsOffTheTable"
    payload: CardsOffTheTableInfo
