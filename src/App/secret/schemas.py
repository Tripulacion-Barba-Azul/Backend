from pydantic import BaseModel
from sqlalchemy import null

class SecretGameInfo(BaseModel):
    secretOwnerID: int
    secretName: str
    revealed: bool

class SecretPublicInfo(BaseModel):
    id: int
    revealed: bool = False
    name: str | None = None

class SecretPrivateInfo(BaseModel):
    id: int
    name: str
    revealed: bool = False
    