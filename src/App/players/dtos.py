from dataclasses import dataclass
from datetime import date

@dataclass
class PlayerDTO:
    name: str
    birthday: date