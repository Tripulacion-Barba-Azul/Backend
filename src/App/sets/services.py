from sqlalchemy.orm import Session

from App.card.models import Card, Detective
from App.players.services import PlayerService
from App.sets.enums import DetectiveSetType
from App.exceptions import NotCardInHand, PlayerNotFoundError
from App.players.models import Player
from App.sets.models import DetectiveSet
from App.players.enums import TurnAction
from App.games.models import Game


class DetectiveSetService:

    def __init__(self, db: Session):
        self._db = db
        self._player_service = PlayerService(db)


    def validate_play_set(self, cards: list[Card]) -> DetectiveSetType | None:
        
        if not all(isinstance(c, Detective) for c in cards):
            return None
        
        if not no_ariadne_oliver(cards):
            return None
        
        if not not_all_wildcards(cards):
            return None
        
        if validate_hercule_poirot_set(cards):
            return DetectiveSetType.HERCULE_POIROT
        
        if validate_miss_marple_set(cards):
            return DetectiveSetType.MISS_MARPLE
        
        if validate_mr_satterthwaite_set(cards):
            return DetectiveSetType.MR_SATTERTHWAITE
        
        if validate_satterthquin_set(cards):
            return DetectiveSetType.SATTERTHQUIN
        
        if validate_parker_pyne_set(cards):
            return DetectiveSetType.PARKER_PYNE
        
        if validate_lady_eileen_brent_set(cards):
            return DetectiveSetType.LADY_EILEEN_BRENT
        
        if validate_tommy_beresford_set(cards):
            return DetectiveSetType.TOMMY_BERESFORD
        
        if validate_tuppence_beresford_set(cards):
            return DetectiveSetType.TUPPENCE_BERESFORD
        
        if validate_siblings_beresford(cards):
            return DetectiveSetType.SIBLINGS_BERESFORD
        
        return None
      

    def create_detective_set(self, player_id: int, card_ids: list[int], set_type: DetectiveSetType):
    
        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        cards_to_set = [card for card in player.cards if card.id in card_ids]

        if len(cards_to_set) != len(card_ids):
            raise NotCardInHand("That card does not belong to the player.")
        
        new_set = DetectiveSet(
            type=set_type,
            player=player,
            cards=cards_to_set
        )
        
        player.cards = [card for card in player.cards if card.id not in card_ids]

        self._db.add(new_set)
        self._db.commit()

        return new_set
    
    def select_event_type(self, game: Game, set_type: DetectiveSetType) -> TurnAction:
        if set_type == DetectiveSetType.HERCULE_POIROT:
            return TurnAction.REVEAL_SECRET
        if set_type == DetectiveSetType.MISS_MARPLE:
            return TurnAction.REVEAL_SECRET
        if set_type == DetectiveSetType.MR_SATTERTHWAITE:
            return TurnAction.SELECT_ANY_PLAYER_SETS
        if set_type == DetectiveSetType.SATTERTHQUIN:
            return TurnAction.SATTERWAITEWILD
        if set_type == DetectiveSetType.PARKER_PYNE:

            revealed_secrets = []
            for player in game.players:
                for secret in player.secrets:
                    if secret.revealed:
                        revealed_secrets.append(secret)

            if not revealed_secrets:
                return TurnAction.NO_EFFECT

            return TurnAction.HIDE_SECRET
        if set_type == DetectiveSetType.LADY_EILEEN_BRENT:
            return TurnAction.SELECT_ANY_PLAYER_SETS
        if set_type == DetectiveSetType.TOMMY_BERESFORD:
            return TurnAction.SELECT_ANY_PLAYER_SETS
        if set_type == DetectiveSetType.TUPPENCE_BERESFORD:
            return TurnAction.SELECT_ANY_PLAYER_SETS
        if set_type == DetectiveSetType.SIBLINGS_BERESFORD:
            return TurnAction.SELECT_ANY_PLAYER_SETS
        

def no_ariadne_oliver(cards: list[Card]) -> bool:

    card_names = [card.name for card in cards]
    return "Ariadne Oliver" not in card_names

def not_all_wildcards(cards: list[Card]) -> bool:
    card_names = [card.name for card in cards]
    return not all(name == "Harley Quin" for name in card_names)


def validate_hercule_poirot_set(cards: list[Card]) -> bool:

    if len(cards) < 3:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Hercule Poirot","Harley Quin"]]
    if detectives:
        return False

    return True
    
def validate_miss_marple_set(cards: list[Card]) -> bool:

    if len(cards) < 3:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Miss Marple","Harley Quin"]]
    if detectives:
        return False

    return True

def validate_mr_satterthwaite_set(cards: list[Card]) -> bool:

    if len(cards) < 2:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Mr Satterthwaite"]]
    if detectives:
        return False

    return True

def validate_satterthquin_set(cards: list[Card]) -> bool:

    if len(cards) < 2:
        return False
    
    if "Harley Quin" not in [card.name for card in cards]:
        return False

    detectives = [card.name for card in cards if card.name not in ["Mr Satterthwaite","Harley Quin"]]
    if detectives:
        return False

    return True

def validate_parker_pyne_set(cards: list[Card]) -> bool:

    if len(cards) < 2:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Parker Pyne","Harley Quin"]]
    if detectives:
        return False

    return True

def validate_lady_eileen_brent_set(cards: list[Card]) -> bool:

    if len(cards) < 2:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Lady Eileen Brent","Harley Quin"]]
    if detectives:
        return False

    return True

def validate_tommy_beresford_set(cards: list[Card]) -> bool:

    if len(cards) < 2:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Tommy Beresford","Harley Quin"]]
    if detectives:
        return False

    return True

def validate_tuppence_beresford_set(cards: list[Card]) -> bool:

    if len(cards) < 2:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Tuppence Beresford","Harley Quin"]]
    if detectives:
        return False

    return True

def validate_siblings_beresford(cards: list[Card]) -> bool:

    if len(cards) < 2:
        return False
    
    detectives = [card.name for card in cards if card.name not in ["Tommy Beresford","Tuppence Beresford","Harley Quin"]]
    if detectives:
        return False

    return True
