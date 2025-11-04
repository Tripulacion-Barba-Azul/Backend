from enum import Enum  

class EventType(Enum):
    PLAY_SET = "play set"
    PLAY_CARD = "play card"
    PLAY_DETECTIVE = "play detective"
    PLAY_NSF = "play NSF"
    RECEIVE_DEVIOUS = "receive devious"
    DISCARD_ETTP = "discard ETTP"
    POINT_YOUR_SUSPICIONS = "point your suspicions"
