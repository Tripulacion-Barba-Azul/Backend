from App.events.resolvers.card_resolvers import (
    AndThereWasOneMoreResolver,
    AnotherVictimResolver,
    CardsOffTheTableResolver, 
    DelayTheMurderersEscapeResolver, 
    EarlyTrainToPaddingtonResolver,
    LookIntoTheAshesResolver
)


CARD_RESOLVER_MAP = {
    "Cards off the table": CardsOffTheTableResolver,
    "Another Victim": AnotherVictimResolver,
    #"Dead Card Folly"
    "Look in to the Ashes": LookIntoTheAshesResolver,
    #"Card Trade"
    "And There was One More...": AndThereWasOneMoreResolver,
    "Delay the Muderer's Escape": DelayTheMurderersEscapeResolver,
    "Early Train to Paddington": EarlyTrainToPaddingtonResolver
    #"Point Your Suspicions"
}

def get_card_resolver(event, db):
    card_name = event.played_card.name
    resolver_cls = CARD_RESOLVER_MAP.get(card_name)
    if not resolver_cls:
        return None
    return resolver_cls(event, db)
