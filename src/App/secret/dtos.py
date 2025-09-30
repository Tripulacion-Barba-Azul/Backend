from pydantic import BaseModel
from enum import Enum

class SecretType(str, Enum):
    ASSASSIN = "Assassin"
    ACOMPLICE = "Acomplice"
    GENERIC = "Generic"


class SecretDTO(BaseModel):
    name:str
    description: str
    type: SecretType
    revealed:bool

        