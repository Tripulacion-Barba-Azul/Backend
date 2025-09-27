from datetime import date
from pydantic import BaseModel

from App.players.dtos import PlayerDTO

class PlayerCreate(BaseModel):
    """
    Schema for creating a new player
    """
    playerName: str
    birthDate: date

    def to_dto(self) -> PlayerDTO:
        return PlayerDTO(
            name=self.playerName,
            birthday=self.birthDate,
        )

class PlayerInfo(BaseModel):
    playerId: int
    playerName: str
    birthDate: date
