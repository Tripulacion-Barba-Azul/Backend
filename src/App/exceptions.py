"""Exceptions"""


class GameNotFoundError(Exception):
    """It is raised when no game is found with the specified ID."""

class GameFullError(Exception):
    """It is raised when a game has reached the maximum number of players."""

class GameAlreadyStartedError(Exception):
    """It is raised when trying to join a game that has already started."""

class WebsocketManagerNotFoundError(Exception):
    """It is raised when no websocket manager is found for a game."""

class NotTheOwnerOfTheGame(Exception):
    """Not the owner of the game, GO AWAY."""

class NotEnoughPlayers(Exception):
    """It is raised when the number of players is lower than the minimum required."""

class PlayerNotFoundError(Exception):
    """It is raised when no player is found with the specified ID."""
    
class NotPlayersTurnError(Exception):
    """It is raised when a player tries to play out of their turn."""

class ObligatoryDiscardError(Exception):
    """It is raised when a player must discard but does not."""

class PlayerHave6CardsError(Exception):
    """It is raised when a player tries to draw a card but already has 6 cards."""

class PlayerNeedSixCardsError(Exception):
    """It is raised when a player tries to end their turn without having six cards."""

class DeckNotFoundError(Exception):
    """It is raised when no deck is found with the specified ID."""

class NotCardInHand(Exception):
    """That card does not belong to the player."""

class InvalididDetectiveSet(Exception):
    """Not a valid detective set. Learn the rules little cheater."""

class SecretAlreadyRevealedError(Exception):
    """Cannot reveal a secret that has already been revealed."""

class SecretNotFoundError(Exception):
    """It is raised when no secret is found with the specified ID."""

class NotPlayableCard(Exception):
    """You tried to play a card that is not playable."""

