from App.events.resolvers.detective_resolvers import AriadneOliverResolver
from App.events.resolvers.play_set_resolver import PlaySetResolver


DEFAULT_DETECTIVE_RESOLVER = PlaySetResolver

SPECIAL_DETECTIVE_RESOLVERS = {
    "Ariadne Oliver": AriadneOliverResolver,
}

def get_detective_resolver(event, db):
    card_name = event.played_card.name
    resolver_cls = SPECIAL_DETECTIVE_RESOLVERS.get(card_name, DEFAULT_DETECTIVE_RESOLVER)
    return resolver_cls(event, db)
