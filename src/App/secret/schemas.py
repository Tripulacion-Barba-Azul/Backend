from pydantic import BaseModel

class SecretGameInfo(BaseModel):
    secretOwnerID: int
    secretName: str
    revealed: bool

