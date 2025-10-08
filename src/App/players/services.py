from sqlalchemy.orm import Session

from App.card.models import Card
from App.players.dtos import PlayerDTO
from App.players.models import Player
from App.secret.models import Secret

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
    
    def get_secrets(self, player_id) -> list[Secret]:
        player = self._db.query(Player).filter_by(id = player_id).first()
        if not player:
            raise Exception(f"Player {player_id} does not exist")
        secrets = player.secrets
        return secrets
    
    def get_cards(self, player_id) -> list[Card]:
        player = self._db.query(Player).filter_by(id = player_id).first()
        if not player:
            raise Exception(f"Player {player_id} does not exist")
        cards = player.cards
        return cards