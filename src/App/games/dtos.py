from dataclasses import dataclass

@dataclass
class GameDTO:
    name: str
    min_players: int
    max_players: int
