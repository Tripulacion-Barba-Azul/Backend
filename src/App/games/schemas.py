from pydantic import BaseModel, Field

from App.card.schemas import CardGameInfo, CardPublicInfo
from App.games.dtos import GameDTO
from App.players.schemas import PlayerGameInfo, PlayerInfo, PlayerPrivateInfo, PlayerPublicInfo, PlayerWinInfo
from App.secret.schemas import SecretGameInfo

class GameCreate(BaseModel):
    """
    Schema for creating a new game
    """
    gameName: str
    minPlayers: int = Field(..., gt=1, lt=7)
    maxPlayers: int = Field(..., gt=1, lt=7)

    def to_dto(self) -> GameDTO:
        return GameDTO(
            name=self.gameName,
            min_players=self.minPlayers,
            max_players=self.maxPlayers,
        )

class GameInfo(BaseModel):
    gameId: int
    ownerId: int


class GameInfoPlayer(BaseModel):
    gameId: int
    actualPlayerId: int

class GameLobbyInfo(BaseModel):
    gameId: int
    gameName: str
    minPlayers: int
    maxPlayers: int
    actualPlayers: int
    ownerName: str

class GameWaitingInfo(BaseModel):
    gameId: int
    gameName: str
    minPlayers: int
    maxPlayers: int
    ownerId: int
    players: list[PlayerInfo]


class GameStartInfo(BaseModel):
    event: str = "game_started"
    turn: int = 1
    playerTurnId: int
    numberOfRemainingCards: int
    players: list[PlayerGameInfo]
    cards: list[CardGameInfo]
    secrets: list[SecretGameInfo]


class GamePublicInfo(BaseModel):
    actionStatus: str  #”blocked” | “unblocked”
    gameStatus: str  #“waiting” | “inProgress” | “finished”
    regularDeckCount: int
    discardPileTop: CardPublicInfo | None
    draftCards:list[CardPublicInfo] = []
    discardPileCount: int = 1
    players: list[PlayerPublicInfo]

class PublicUpdate(BaseModel):
    event: str = "publicUpdate"
    payload: GamePublicInfo

class PrivateUpdate(BaseModel):
    event: str = "privateUpdate"
    payload: PlayerPrivateInfo

class GameEndInfo(BaseModel):
    event: str = "gameEnded"
    payload: list[PlayerWinInfo]


