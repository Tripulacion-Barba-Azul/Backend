from enum import Enum

class GameStatus(Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class ActionStatus(Enum):
    BLOCKED = "blocked"
    UNBLOCKED = "unblocked"

class Winners(Enum):
    DETECTIVE = "detective"
    MURDERER = "murderer"