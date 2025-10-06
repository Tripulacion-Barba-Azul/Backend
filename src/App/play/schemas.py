from pydantic import BaseModel

from App.card.schemas import CardGameInfo
from App.players.schemas import PlayerGameInfo
    
class PlayCardInfo(BaseModel):
    event: str = "play_card"
    players: list[PlayerGameInfo]
    cards: list[CardGameInfo]