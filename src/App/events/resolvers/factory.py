from App.events.enums import EventType
from App.events.resolvers.discard_ettp_resolver import DiscardETTPResolver
from App.events.resolvers.play_set_resolver import PlaySetResolver
from App.events.resolvers.play_card_resolver import PlayCardResolver
from App.events.resolvers.play_detective_resolver import PlayDetectiveResolver

RESOLVER_MAP = {
    EventType.PLAY_SET: PlaySetResolver,
    EventType.PLAY_CARD: PlayCardResolver,
    EventType.PLAY_DETECTIVE: PlayDetectiveResolver,
    EventType.DISCARD_ETTP: DiscardETTPResolver
}

def get_resolver(event, db):
    resolver_cls = RESOLVER_MAP.get(event.type)
    if not resolver_cls:
        return None
    return resolver_cls(event, db)
