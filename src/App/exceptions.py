"""Exceptions"""

class GameNotFoundError(Exception):
    """Se lanza cuando no se encuentra un juego con el id especificado."""
    pass


class GameFullError(Exception):
    """Se lanza cuando un juego ya alcanzó el número máximo de jugadores."""
    pass


class GameAlreadyStartedError(Exception):
    """Se lanza cuando se intenta unir a un juego que ya ha comenzado."""
    pass

class WebsocketManagerNotFoundError(Exception):
    """Se lanza cuando no se encuentra un manejador de websockets para un juego."""
    pass