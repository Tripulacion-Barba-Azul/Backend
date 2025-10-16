from enum import Enum

class PlayerRole(Enum):
    DETECTIVE = "detective"
    MURDERER = "murderer"
    ACCOMPLICE = "accomplice"

class TurnStatus(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    TAKING_ACTION = "takingAction"
    DISCARDING = "discarding"
    DISCARDING_OPT = "discardingOpt"
    DRAWING = "drawing"

class TurnAction(Enum):
    NO_ACTION = "noAction"
    CARDS_OFF_THE_TABLE = "selectAnyPlayer"
    SELECT_ANY_PLAYER = "selectAnyPlayer"
    ONE_MORE = "andThenThereWasOneMore"
    SATTERWAITEWILD =  "selectAnyPlayer"
    REVEAL_SECRET = "revealSecret" 
    REVEAL_OWN_SECRET = "revealOwnSecret"
    GIVE_SECRET_AWAY = "revealOwnSecret"
    HIDE_SECRET = "hideSecret"  # All
    HIDE_OWN_SECRET = "hideOwnSecret" 
    STEAL_SET = "stealSet"
    LOOK_INTO_THE_ASHES = "lookIntoTheAshes"
    DELAY_THE_MURDERER = "delayTheMurderer"
    NO_EFFECT = "notifierNoEffect" # Dont use as state in player
