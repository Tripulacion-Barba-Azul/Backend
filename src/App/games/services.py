from App.card.schemas import CardGameInfo
from App.games.utils import db_game_2_game_public_info
from App.decks.reposition_deck_services import RepositionDeckService
from App.games.enums import GameStatus
from App.games.schemas import GameStartInfo
from App.players.schemas import PlayerGameInfo
from App.secret.schemas import SecretGameInfo
from sqlalchemy.orm import Session

from App import players
from App.games.dtos import GameDTO
from App.games.models import Game, Player
from App.games.enums import GameStatus
from App.players.dtos import PlayerDTO
from App.players.enums import PlayerRole, TurnStatus
from App.players.services import PlayerService
from App.exceptions import GameNotFoundError, GameFullError, GameAlreadyStartedError, NotEnoughPlayers, NotTheOwnerOfTheGame
from App.players.utils import sort_players
from App.secret.enums import SecretType
from App.secret.services import create_and_draw_secrets


class GameService:

    def __init__(self, db: Session):
        self._db = db
        self._player_service = PlayerService(db)

    def get_games(self) -> list[Game]:
        query = self._db.query(Game).filter(Game.status==GameStatus.WAITING)
        return query.all()
    
    def get_by_id(self, id: int) -> Game | None:
        return self._db.query(Game).filter(Game.id == id).first()

    def create(
            self, 
            player_dto: PlayerDTO,
            game_dto: GameDTO
    ) -> Game:

        if game_dto.max_players < game_dto.min_players:
            raise ValueError("El máximo de jugadores debe ser mayor o igual al mínimo.")

        owner = self._player_service.create(player_dto)
        new_game: Game = Game(
            name=game_dto.name,
            min_players=game_dto.min_players,
            max_players=game_dto.max_players,
            owner=owner,
        )

        self._db.add(new_game)
        self._db.flush()
        self._db.commit()

        return new_game
    
    def join(
            self, 
            game_id: int, 
            player_dto: PlayerDTO
    ) -> tuple[Game, Player]:

        game: Game | None = self._db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise GameNotFoundError(f"El juego con id {game_id} no existe.")
        
        if game.status != GameStatus.WAITING:
            raise GameAlreadyStartedError("No se puede unir a un juego que ya ha comenzado.")
        
        if len(game.players) >= game.max_players:
            raise GameFullError("El juego ya ha alcanzado el número máximo de jugadores.")

        new_player = self._player_service.create(player_dto)
        game.players.append(new_player)
        game.num_players += 1

        self._db.add(game)
        self._db.flush()
        self._db.commit()

        return game, new_player
    

    def start_game(
            self,
            game_id: int,
            owner_id: int
    ) -> Game:
        db_game: Game | None = self._db.query(Game).filter(Game.id == game_id).first()
        if not db_game:
            raise GameNotFoundError("Se lanza cuando no se encuentra un juego con el id especificado.")
        
        if db_game.owner_id != owner_id:
            raise NotTheOwnerOfTheGame("Not the owner of the game, GO AWAY.")
        
        if db_game.min_players > db_game.num_players:
            raise NotEnoughPlayers("Number of players lower than minimun required.")
        
        if db_game.status != GameStatus.WAITING:
            raise GameAlreadyStartedError("Se lanza cuando se intenta iniciar un juego que ya ha comenzado.")
        
        #  actualizar base de datos
        db_game.status = GameStatus.IN_PROGRESS
        db_game.turn_number = 1

        # ordenar jugadores
        players = sort_players(db_game.players)
        for idx, player in enumerate(players):
            player.turn_order = idx + 1

        self.select_player_turn(game_id)
        # asignar roles jugador
        create_and_draw_secrets(game_id, self._db)
        murderer = None
        accomplice = None
        for player in players:
            for secret in player.secrets:
                if secret.type == SecretType.MURDERER:
                    player.role = PlayerRole.MURDERER
                    murderer = player
                elif secret.type == SecretType.ACCOMPLICE:
                    player.role = PlayerRole.ACCOMPLICE
                    accomplice = player

        if accomplice and murderer:
            murderer.ally = accomplice.id
            accomplice.ally = murderer.id        

        self._db.commit()

        # inicializa mazo
        RepositionDeckService(self._db).create_reposition_deck(game_id)
        RepositionDeckService(self._db).draw_reposition_deck(game_id)

        return db_game
            
    def select_player_turn(self, game_id) -> int:
        db_game: Game | None = self._db.query(Game).filter(Game.id == game_id).first()
        if not db_game:
            raise GameNotFoundError("Se lanza cuando no se encuentra un juego con el id especificado.")
        
        player_order_number = (db_game.turn_number-1) % db_game.num_players + 1

        for p in db_game.players:
            if p.turn_order == player_order_number:
                player = p
                p.turn_status = TurnStatus.PLAYING
                if p.in_social_disgrace:
                    p.turn_status = TurnStatus.DISCARDING
                self._db.add(p)
                self._db.flush()
                self._db.commit()
        
        return player.id # type: ignore
        
    def player_in_game(self, game_id: int, player_id: int) -> bool:
        db_game: Game | None = self._db.query(Game).filter(Game.id == game_id).first()
        if not db_game:
            raise GameNotFoundError("Se lanza cuando no se encuentra un juego con el id especificado.")
        
        b = False
        for p in db_game.players:
            if p.id == player_id:
                b = True
        
        return b

