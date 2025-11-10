from enum import Enum  

class EventType(Enum):
    PLAY_SET = "play set"
    PLAY_CARD = "play card"
    PLAY_DETECTIVE = "play detective"
    PLAY_NSF = "play NSF"
    RECEIVE_DEVIOUS = "receive devious"
    DISCARD_ETTP = "discard ETTP"
    POINT_YOUR_SUSPICIONS = "point your suspicions"
    POINT_YOUR_SUSPICIONS_MAIN = "point your suspicions main"
    CARD_TRADE = "card trade"
    DEAD_CARD_FOLLY = "dead card folly"
    DEAD_CARD_FOLLY_DIRECTION = "dead card folly direction"

class Direction(Enum):
    CLOCKWISE = "left"
    COUNTERCLOCKWISE = "right"
