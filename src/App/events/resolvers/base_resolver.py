from abc import ABC, abstractmethod

class BaseEventResolver(ABC):
    def __init__(self, event, db):
        self.event = event
        self._db = db

    @abstractmethod
    def resolve(self):
        """Resolves the event"""
        pass
