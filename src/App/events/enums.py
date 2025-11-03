from enum import Enum  

class EventType(Enum):
    PLAY_SET = "play_set"
    PLAY_CARD = "play_card"
    ADD_DETECTIVE_TO_SET = "add_detective_to_set"
    PLAY_NSF = "play_NSF"
    RECEIVE_DEVIOUS = "receive_devious"
    DISCARD_ETTP = "discard_ETTP"
    POINT_YOUR_SUSPICIONS = "point_your_suspicions"
