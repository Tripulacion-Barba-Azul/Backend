from pydantic import BaseModel, Field

from App.games.dtos import GameDTO

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