from enum import Enum

class TurnStatus(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    DISCARDING = "discarding"
    DRAWING = "drawing"