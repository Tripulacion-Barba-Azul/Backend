from datetime import date
import pytest
from sqlalchemy.orm import Session

from App.games.dtos import GameDTO
from App.games.models import Game
from App.games.services import GameService
from App.play.services import PlayService
from App.players.dtos import PlayerDTO
from App.players.models import Player


@pytest.fixture(name="sample_player")
def sample_player(session:Session):
    player = Player(name="Elias", avatar="kjhgdsFAKJHG", birthday= date(1999,3,13))
    session.add(player)
    session.commit()
    session.refresh(player)
    return player

@pytest.fixture(name="sample_game")
def sample_game(session, sample_player):
    """Fixture para crear un game de prueba"""
    game = Game(
        name="test_game",
        min_players=2,
        max_players=4,
        owner= sample_player
    )
    session.add(game)
    session.commit()
    session.refresh(game)
    return game

@pytest.fixture(name="seed_started_game")
def seed_started_game(session: Session):
    def _create(num_players: int):
        owner = PlayerDTO(name="Barba Azul",avatar=1, birthday=date(1980,10,10))
        game_dto = GameDTO(
            name=f"Tripulación de Barba Azul ({num_players})",
            min_players=2,
            max_players=num_players,
        )
        game = GameService(session).create(owner, game_dto)

        for i in range(2, num_players + 1):
            player = PlayerDTO(
                name=f"Player {i}",
                avatar=1,
                birthday=date(1990+i,(7+i) % 13,13+i) # Player 2 always start,
            )
            GameService(session).join(game_id=game.id, player_dto=player)

        game = GameService(session).start_game(
            game_id=game.id,
            owner_id=game.owner_id,
        )

        return game
    return _create

@pytest.fixture(name="seed_game_player2_discard")
def seed_game_player2_discard(session: Session, seed_started_game):
    game = seed_started_game(4)
    player = game.players[1]
    PlayService(session).no_action(game.id, player.id)
    
    return game, player

@pytest.fixture(name="seed_game_player2_draw")
def seed_game_player2_draw(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    cards_id = [card.id for card in player.cards]
    PlayService(session).discard(game, player.id, cards_id)
    
    return game, player

