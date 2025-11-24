from datetime import date
from pydantic import BaseModel

from src.App.card.schemas import CardPrivateInfo, CardPublicInfo
from src.App.players.dtos import PlayerDTO
from src.App.players.enums import TurnStatus
from src.App.secret.schemas import SecretPrivateInfo, SecretPublicInfo
from src.App.sets.schemas import SetPublicInfo

class PlayerCreate(BaseModel):
    """
    Schema for creating a new player
    """
    playerName: str
    avatar: int
    birthDate: date

    def to_dto(self) -> PlayerDTO:
        return PlayerDTO(
            name=self.playerName,
            avatar=self.avatar,
            birthday=self.birthDate,
        )

class PlayerInfo(BaseModel):
    playerId: int
    playerName: str
    birthDate: date

class PlayerPlaysIn(BaseModel):
    games: list[dict[str, int]]

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
    socialDisgrace: bool
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

class PlayerPlayedCardsInfo(BaseModel):
    playerId: int
    cards: list[CardPublicInfo]
    actionType: str

class CardsPlayedInfo(BaseModel):
    event: str = "notifierCardsPlayed"
    payload: PlayerPlayedCardsInfo

class PlayerPlayedDetectiveInfo(BaseModel):
    playerId: int
    cards: list[CardPublicInfo]
    actionType: str
    setOwnerId: int

class DetectiveCardsPlayedInfo(BaseModel):
    event: str = "notifierCardsPlayed"
    payload: PlayerPlayedDetectiveInfo

