from datetime import date
from pydantic import BaseModel

from App.card.schemas import CardPrivateInfo
from App.players.dtos import PlayerDTO
from App.players.enums import TurnStatus
from App.secret.schemas import SecretPrivateInfo, SecretPublicInfo
from App.sets.schemas import SetPublicInfo

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

class PlayerGameInfo(BaseModel):
    id: int
    name: str
    rol: str
    
class PlayerWinInfo(BaseModel):
    name: str
    role: str

class PlayerPublicInfo(BaseModel):
    id: int
    name: str
    avatar: int
    turnOrder: int
    turnStatus: str
    cardCount: int
    secrets: list[SecretPublicInfo]
    sets: list[SetPublicInfo] = []


class AllyInfo(BaseModel):
    id: int
    role: str

class PlayerPrivateInfo(BaseModel):
    cards: list[CardPrivateInfo]
    secrets: list[SecretPrivateInfo]
    role: str
    ally: AllyInfo | None = None