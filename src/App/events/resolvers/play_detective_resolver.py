from App.events.resolvers.base_resolver import BaseEventResolver
from App.events.resolvers.detective_factory import get_detective_resolver


class PlayDetectiveResolver(BaseEventResolver):

    def resolve(self):
        resolver = get_detective_resolver(self.event, self._db)
        if resolver is None:
            raise ValueError(f"No resolver found for detective type {self.event.played_card.name}")

        return resolver.resolve()
