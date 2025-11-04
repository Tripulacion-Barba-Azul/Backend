from App.events.resolvers.base_resolver import BaseEventResolver
from App.players.enums import TurnAction, TurnStatus
from App.card.services import CardService
from App.play.services import PlayService


class CardsOffTheTableResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        return turn_action
    
class AnotherVictimResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        return turn_action


class LookIntoTheAshesResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        top_cards = PlayService(self._db).get_top_five_discarded_cards(player, game.id)
        return turn_action, top_cards


class AndThereWasOneMoreResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        return turn_action

class DelayTheMurderersEscapeResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        top_cards = PlayService(self._db).get_top_five_discarded_cards(player, game.id)
        return turn_action, top_cards


class EarlyTrainToPaddingtonResolver(BaseEventResolver):

    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        PlayService(self._db).early_train_to_paddington(game, player)
        return turn_action
