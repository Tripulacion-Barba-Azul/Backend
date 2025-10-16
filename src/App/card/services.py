from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from App.card.models import Card, Devious, Detective, Instant, Event
from App.decks.reposition_deck_model import RepositionDeck
from App.players.models import Player
from App.players.enums import TurnAction


class CardService:

    def __init__(self, db: Session):
        self._db = db

    def get_card(self, card_id):
        card = self._db.query(Card).filter_by(id = card_id).first()
        if card == None:
            raise ValueError(f"Card with id:{card_id} dont exist")
        else:
            return card

    def create_devious_card(self, card_name, card_effect):
        new_devious = Devious(
                                name = card_name,
                                effect = card_effect,
                                playable_on_turn = False
                                )
        self._db.add(new_devious)
        self._db.commit()
        self._db.refresh(new_devious)
        return new_devious

    def create_detective_card(self,
                            card_name,
                            card_effect,
                            card_number_to_set
                            
                            ):
        try:
            new_detective = Detective(
                                        name = card_name,
                                        effect = card_effect,
                                        playable_on_turn = True,
                                        number_to_set = card_number_to_set
                                        )
            self._db.add(new_detective)
            self._db.commit()
            self._db.refresh(new_detective)
            return new_detective
        
        except SQLAlchemyError as e:
            self._db.rollback()
            raise ValueError(f"Error creating detective card: {e}")      

    def create_instant_card(self,card_name, card_effect):

        try:
            new_instant = Instant(
                                    name = card_name,
                                    effect = card_effect,
                                    playable_on_turn = True,
                                    playable = True,
                                    )
            self._db.add(new_instant)
            self._db.commit()
            self._db.refresh(new_instant)
            return new_instant
        except SQLAlchemyError as e:
            self._db.rollback()
            raise ValueError(f"Error creating instant card: {e}")
        
    def create_event_card(self, card_name, card_effect):
        
        try:
            new_event = Event(
                                name = card_name,
                                effect = card_effect,
                                playable_on_turn = True,
                                )
            self._db.add(new_event)
            self._db.commit()
            self._db.refresh(new_event)

            return new_event

        except SQLAlchemyError as e:
            self._db.rollback()
            raise ValueError(f"Error creating event card: {e}")

    def relate_card_reposition_deck(self, deck_id, card_id, commit=False):
        card = CardService(self._db).get_card(card_id)
        reposition_deck = self._db.query(RepositionDeck).filter_by(id = deck_id).first()

        if reposition_deck == None:
            raise ValueError(
                f"Reposition Deck with id {deck_id} dont exist"
            )
        else:
            reposition_deck.number_of_cards += 1
            card.order = reposition_deck.number_of_cards
            reposition_deck.cards.append(card)
            self._db.commit()
            self._db.refresh(reposition_deck)
            self._db.refresh(card)

    def unrelate_card_reposition_deck( self, deck_id, card_id, commit=False):
        reposition_deck = self._db.query(RepositionDeck).filter_by(id=deck_id).first()
        if not reposition_deck:
            raise ValueError(f"Reposition deck with id {deck_id} not found")
        
        card = CardService(self._db).get_card(card_id) 

        if card not in reposition_deck.cards:
            raise ValueError(f"Card {card_id} not in reposition deck {deck_id}")
        
        reposition_deck.cards.remove(card)
        reposition_deck.number_of_cards -= 1

        if commit:
            self._db.commit()
            self._db.refresh(reposition_deck)
            
    def relate_card_player(self, player_id, card_id, commit=False):
        player = self._db.query(Player).filter_by(id=player_id).first()
        card = CardService(self._db).get_card(card_id)

        if player is None:
            raise ValueError(f"Player with id {player_id} not found")
        if card is None:
            raise ValueError(f"Card with id {card_id} not found")

        player.cards.append(card)

        if commit:
            self._db.commit()
            self._db.refresh(player)

    def unrelate_card_player(self, card_id, player_id):
        player = self._db.query(Player).filter_by(id = player_id).first()
        card = CardService(self._db).get_card(card_id)

        if card in player.cards: # type: ignore
            player.cards.remove(card) # type: ignore
            self._db.commit()
            self._db.refresh(player)
            self._db.refresh(card)
        else:
            raise ValueError(
                f"Card with {card_id} not related with player {player_id}"
            )
        
    def select_event_type(self, game, player, card) -> TurnAction:
        if card.name == "Another Victim":
            return another_victim_event_type(game,player)
        elif card.name == "And There was One More...":
            return and_then_there_was_one_more_event_type(game)
        elif card.name == "Look Into The Ashes":
            return TurnAction.LOOK_INTO_THE_ASHES
        else:
            return TurnAction.NO_ACTION

def another_victim_event_type(game, player) -> TurnAction:
    player_id = player.id
    players = game.players
    dsets = []
    for player in players:
        if player.id != player_id:
            dsets += [dset for dset in player.sets]
    
    if not dsets:
        return TurnAction.NO_EFFECT
    return TurnAction.STEAL_SET

def and_then_there_was_one_more_event_type(game) -> TurnAction:
    
    revealed_secrets = []
    for player in game.players:
        for secret in player.secrets:
            if secret.revealed:
                revealed_secrets.append(secret)

    if not revealed_secrets:
        return TurnAction.NO_EFFECT
    return TurnAction.ONE_MORE


    