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
    CARDS_OFF_THE_TABLE = "selectAnyPlayer" # este repite SAP
    SELECT_ANY_PLAYER = "SELECT_ANY_PLAYER" # este repite SAP
    ONE_MORE = "andThenThereWasOneMore"
    SATTERWAITEWILD =  "SATTERWAITEWILD" # este repite SAP
    REVEAL_SECRET = "revealSecret" 
    REVEAL_OWN_SECRET = "revealOwnSecret" # este repite ROS
    GIVE_SECRET_AWAY = "GIVE_SECRET_AWAY" # este repite ROS
    HIDE_SECRET = "hideSecret"  # All
    HIDE_OWN_SECRET = "hideOwnSecret" 
    STEAL_SET = "stealSet"
    LOOK_INTO_THE_ASHES = "lookIntoTheAshes"
    DELAY_THE_MURDERER = "delayTheMurderer"
    NO_EFFECT = "notifierNoEffect" # Dont use as state in player

