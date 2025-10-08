from pydantic import BaseModel

class CardDTO(BaseModel):
    name: str
    effect:str

class DeviousDTO(CardDTO):
    playable_on_turn :bool 
    
    def playable(self):
        pass


class DetectiveDTO(CardDTO):    
    number_to_set:int
    playable_on_turn: bool

    def playable(self, current_turn):
        return self.playable_on_turn and current_turn
    

    
class EventDTO(CardDTO):
    playable_on_turn: bool

    def playable(self, is_your_turn):
        return self.playable_on_turn and is_your_turn
    

    
class InstantDTO(CardDTO):

    def playable(self, game):
        action_made =game.action_made #Representa que se realizo una accion en el juego
        return action_made

