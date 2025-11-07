from App.events.resolvers.base_resolver import BaseEventResolver
from App.players.enums import TurnAction, TurnStatus
from App.sets.services import DetectiveSetService


class PlayDetectiveResolver(BaseEventResolver):

    def resolve(self):
        game = self.event.game
        player = self.event.selected_player
        return_player = self.event.main_player
        dset = self.event.dset
        card = self.event.played_card

        if card.name == "Ariadne Oliver":
            player.turn_action = TurnAction.REVEAL_OWN_SECRET
        
        else:
            turn_action = DetectiveSetService(self._db).select_event_type(game, dset.type)
            
            if turn_action == TurnAction.NO_EFFECT:
                player.turn_action = TurnAction.NO_ACTION
                
            else :
                player.turn_action = turn_action
                

        return_player.turn_action = TurnAction.NO_ACTION
        return_player.turn_status = TurnStatus.TAKING_ACTION
        

        self._db.flush()
        self._db.commit()

        return turn_action
