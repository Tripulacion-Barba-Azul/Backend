from pydantic import BaseModel

class SecretGameInfo(BaseModel):
    secretOwnerID: int
    secretName: str
    revealed: bool

class SecretPublicInfo(BaseModel):
    id: int
    revealed: bool = False
    name: str = None
        