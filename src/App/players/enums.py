from enum import Enum

class PlayerRol(Enum):
    DETECTIVE = "detective"
    MURDERER = "murderer"
    ACCOMPLICE = "accomplice"

class TurnStatus(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    DISCARDING = "discarding"
    DISCARDING_OPT = "discardingOpt"
    DRAWING = "drawing"