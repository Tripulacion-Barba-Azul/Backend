from sqlalchemy.orm import Session

from App.players.dtos import PlayerDTO
from App.players.models import Player

class PlayerService:

    def __init__(self, db: Session):
        self._db = db

    def create(self, player_dto: PlayerDTO) -> Player:
        new_player = Player(
            name=player_dto.name,
            birthday=player_dto.birthday
        )
        self._db.add(new_player)
        self._db.flush()
        self._db.commit()
        return new_player
    