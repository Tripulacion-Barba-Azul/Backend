"""Defines project settings"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Project settings definition"""

    ROOT_PATH: str = ""
    DB_FILEANAME: str = "sqlite:///deathonthecards.db"



settings = Settings()
