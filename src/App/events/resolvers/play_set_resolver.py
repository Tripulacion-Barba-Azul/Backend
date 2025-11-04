from App.events.resolvers.base_resolver import BaseEventResolver
from App.players.enums import TurnAction, TurnStatus
from App.sets.services import DetectiveSetService


class PlaySetResolver(BaseEventResolver):

    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        dset = self.event.dset
        turn_action = DetectiveSetService(self._db).select_event_type(game, dset.type)
        
        if turn_action == TurnAction.NO_EFFECT:
            player.turn_action = TurnAction.NO_ACTION
            player.turn_status = TurnStatus.DISCARDING_OPT
        else :
            player.turn_action = turn_action
            player.turn_status = TurnStatus.TAKING_ACTION

        self._db.flush()
        self._db.commit()

        return turn_action
