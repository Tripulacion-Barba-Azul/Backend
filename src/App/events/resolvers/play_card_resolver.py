from App.events.resolvers.base_resolver import BaseEventResolver
from App.events.resolvers.card_factory import get_card_resolver

class PlayCardResolver(BaseEventResolver):
    
    def resolve(self):
        resolver = get_card_resolver(self.event, self._db)
        if resolver is None:
            raise ValueError(f"No resolver found for card type {self.event.played_card.name}")

        return resolver.resolve()
