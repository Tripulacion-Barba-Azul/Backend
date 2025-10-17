
from pydantic import BaseModel

from App.card.schemas import CardGameInfo, CardPublicInfo
from App.players.schemas import PlayerGameInfo
from App.card.schemas import CardGameInfo
    
class PlayCardInfo(BaseModel):
    event: str = "play_card"
    players: list[PlayerGameInfo]
    cards: list[CardGameInfo]
    
class PlayCard(BaseModel):
    playerId: int
    cards: list[int]

class DrawCardInfo(BaseModel):
    playerId: int
    deck: str
    order: int | None = None
    
class SelectAnyPlayerInfo(BaseModel):
    playerId: int
    selectedPlayerId: int
    
class CardsOffTheTableInfo(BaseModel):
    playerId: int
    quantity: int
    selectedPlayerId: int
    
class NotifierCardsOffTheTable(BaseModel):
    event: str = "notifierCardsOffTheTable"
    payload: CardsOffTheTableInfo
    
class RevealSecretInfo(BaseModel):
    playerId: int
    secretId: int
    revealedPlayerId: int

class StealSetInfo(BaseModel):
    playerId: int
    stolenPlayerId: int
    setId: int

class NotifierStealSet(BaseModel):
    event: str =  "notifierStealSet"
    payload: StealSetInfo


class HideSecretInfo(BaseModel):
    playerId: int
    secretId: int
    hiddenPlayerId: int

class PayloadHideSecret(BaseModel):
    playerId: int
    secretId: int
    selectedPlayerId: int

class NotifierHideSecret(BaseModel):
    event: str = "notifierHideSecret"
    payload:  PayloadHideSecret


class AndThenThereWasOneMoreInfo(BaseModel):
    playerId: int
    secretId: int
    stolenPlayerId: int
    selectedPlayerId: int


class PayloadAndThenThereWasOneMore(BaseModel):
    playerId: int
    secretId: int
    secretName: str
    stolenPlayerId: int
    giftedPlayerId: int


class NotifierAndThenThereWasOneMore(BaseModel):
    event: str =  "notifierAndThenThereWasOneMore"
    payload: PayloadAndThenThereWasOneMore

class LookIntoTheAshesInfo(BaseModel):
    playerId: int
    cardId: int

class PayloadLookIntoTheAshes(BaseModel):
    playerId: int
    

class NotifierLookIntoTheAshes(BaseModel):
    event: str = "notifierLookIntoTheAshes"
    payload: PayloadLookIntoTheAshes

class RevealOwnSecretInfo(BaseModel):
    playerId: int
    secretId : int


class PayloadSatterthwaiteWild(BaseModel):
    playerId: int
    secretId: int
    secretName: str
    selectedPlayerId: int


class NotifierSatterthwaiteWild(BaseModel):
    event: str = "notifierSatterthwaiteWild"
    payload: PayloadSatterthwaiteWild

class PayloadRevealSecretForce(BaseModel):
    playerId: int
    secretId: int
    selectedPlayerId: int

class NotifierRevealSecretForce(BaseModel):
    event: str = "notifierRevealSecretForce"
    payload: PayloadRevealSecretForce
