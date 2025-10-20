from dataclasses import dataclass
from datetime import date

@dataclass
class PlayerDTO:
    name: str
    avatar: int
    birthday: date