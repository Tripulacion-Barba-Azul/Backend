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


def test_draw_card_from_deck_success(session: Session, seed_game_player2_draw):
    game = seed_game_player2_draw[0]
    player = seed_game_player2_draw[1]
    rep_deck_len = len(game.reposition_deck.cards)

    PlayService(session).draw_card_from_deck(game.id, player.id)    

    assert len(player.cards) == 1
    assert player.turn_status == TurnStatus.DRAWING
    assert rep_deck_len - 1 == len(game.reposition_deck.cards)

def test_draw_card_from_deck_6_cards_error(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]

    PlayService(session).discard(game, player.id, [card.id])
    
    PlayService(session).draw_card_from_deck(game.id, player.id)    

    try:
        PlayService(session).draw_card_from_deck(game.id, player.id)    
        assert False
    except Exception as e:
        assert str(e) == f"Player {player.id} already has 6 cards"

def test_end_turn_success(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]

    PlayService(session).discard(game, player.id, [card.id])
    PlayService(session).draw_card_from_deck(game.id, player.id)
    
    PlayService(session).end_turn(game.id, player.id) 

    assert player.turn_status == TurnStatus.WAITING
    assert game.turn_number == 2

def test_end_turn_need_six_cards_error(session: Session, seed_game_player2_discard):
    game = seed_game_player2_discard[0]
    player = seed_game_player2_discard[1]
    card = player.cards[0]
    card2 = player.cards[1]

    PlayService(session).discard(game, player.id, [card.id, card2.id])

    PlayService(session).draw_card_from_deck(game.id, player.id)
    
    try:
        PlayService(session).end_turn(game.id, player.id) 
        assert False
    except Exception as e:
        assert str(e) == f"Player {player.id} needs to have six cards to end turn"