from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from App.card.models import Card, Devious, Detective, Instant, Event
from App.decks.reposition_deck_model import RepositionDeck
from App.players.models import Player


def get_card(card_id, db:Session):
    card = db.query(Card).filter_by(id = card_id).first()
    if card == None:
        raise ValueError(f"Card with id:{card_id} dont exist")
    else:
        return card



def create_devious_card(card_name, card_effect, db:Session):
    new_devious = Devious(
                            name = card_name,
                            effect = card_effect,
                            playable_on_turn = False
                            )
    db.add(new_devious)
    db.commit()
    db.refresh(new_devious)
    return new_devious



def create_detective_card(card_name,
                          card_effect,
                          card_number_to_set,
                          db:Session):
    try:
        new_detective = Detective(
                                    name = card_name,
                                    effect = card_effect,
                                    playable_on_turn = True,
                                    number_to_set = card_number_to_set
                                    )
        db.add(new_detective)
        db.commit()
        db.refresh(new_detective)
        return new_detective
    
    except SQLAlchemyError as e:
        db.rollback()
        raise ValueError(f"Error creating detective card: {e}")
    


def create_instant_card(card_name, card_effect, db:Session):

    try:
        new_instant = Instant(
                                name = card_name,
                                effect = card_effect,
                                playable_on_turn = True,
                                playable = True,
                                )
        db.add(new_instant)
        db.commit()
        db.refresh(new_instant)
        return new_instant
    except SQLAlchemyError as e:
        db.rollback()
        raise ValueError(f"Error creating instant card: {e}")
    


def create_event_card(card_name, card_effect, db:Session):
    
    try:
        new_event = Event(
                            name = card_name,
                            effect = card_effect,
                            playable_on_turn = True,
                            )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        return new_event

    except SQLAlchemyError as e:
        db.rollback()
        raise ValueError(f"Error creating event card: {e}")



def relate_card_with_reposition_deck(deck_id, card_id, db:Session):
    card = get_card(card_id, db)
    reposition_deck = db.query(RepositionDeck).filter_by(id = deck_id).first()

    if reposition_deck == None:
        raise ValueError(
            f"Reposition Deck with id {deck_id} dont exist"
        )
    else:
        reposition_deck.cards.append(card)
        db.commit()
        db.refresh(reposition_deck)
        db.refresh(card)



def unrelate_card_reposition_deck(deck_id, card_id, db: Session, commit=False):
    reposition_deck = db.query(RepositionDeck).filter_by(id=deck_id).first()
    if not reposition_deck:
        raise ValueError(f"Reposition deck with id {deck_id} not found")
    
    card = get_card(card_id, db) 

    if card not in reposition_deck.cards:
        raise ValueError(f"Card {card_id} not in reposition deck {deck_id}")
    
    reposition_deck.cards.remove(card)

    if commit:
        db.commit()
        db.refresh(reposition_deck)
        


def relate_card_player(player_id, card_id, db: Session, commit=False):
    player = db.query(Player).filter_by(id=player_id).first()
    card = get_card(card_id, db)

    if player is None:
        raise ValueError(f"Player with id {player_id} not found")
    if card is None:
        raise ValueError(f"Card with id {card_id} not found")

    player.cards.append(card)

    if commit:
        db.commit()
        db.refresh(player)


def unrelate_card_player(card_id, player_id, db:Session):
    player = db.query(Player).fliter_by(id = player_id).first()
    card = get_card(card_id, db)

    if card in player.cards:
        player.cards.remove(card)
        db.commit
        db.refresh(player)
        db.refresh(card)
    else:
        raise ValueError(
            f"Card with {card_id} not related with player {player_id}"
        )
