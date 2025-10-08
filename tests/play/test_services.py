from sqlalchemy.orm import Session

from App.games.models import Game
from App.play.services import PlayService
from App.players.enums import TurnStatus


def test_discard_card_service(session: Session, seed_game_player2_discard):
    game: Game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]

    cards_id = [card.id for card in player.cards]

    PlayService(session).discard(game, player.id, cards_id)    

    assert len(player.cards) == 0
    assert player.turn_status == TurnStatus.DRAWING
    assert len(game.discard_deck.cards) == 7
