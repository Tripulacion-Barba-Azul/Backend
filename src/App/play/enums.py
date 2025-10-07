from enum import Enum

class TurnStatus(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    DISCARDING = "discarding"
    DISCARDING_OPT = "discarding_opt"
    DRAWING = "drawing"