from sqlalchemy.orm import Session

from App.card.services import CardService
from App.sets.enums import DetectiveSetType
from App.sets.services import SetService


def test_valid_hercule_poirot_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Hercule Poirot","",3))
    cards.append(CardService(session).create_detective_card("Hercule Poirot","",3))
    cards.append(CardService(session).create_detective_card("Harley Quin","",0))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.HERCULE_POIROT

def test_invalid_hercule_poirot_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Hercule Poirot","",3))
    cards.append(CardService(session).create_detective_card("Hercule Poirot","",3))
    cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))

    assert SetService(session).validate_play_set(cards) is None

def test_valid_miss_marple_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Miss Marple","",3))
    cards.append(CardService(session).create_detective_card("Miss Marple","",3))
    cards.append(CardService(session).create_detective_card("Miss Marple","",3))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.MISS_MARPLE

def test_invalid_miss_marple_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Miss Marple","",3))
    cards.append(CardService(session).create_detective_card("Miss Marple","",3))

    assert SetService(session).validate_play_set(cards) is None

def test_valid_mr_satterthwaite_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Mr Satterthwaite","",2))
    cards.append(CardService(session).create_detective_card("Mr Satterthwaite","",2))
    cards.append(CardService(session).create_detective_card("Mr Satterthwaite","",2))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.MR_SATTERTHWAITE

def test_invalid_mr_satterthwaite_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Mr Satterthwaite","",2))
    cards.append(CardService(session).create_detective_card("Ariadne Oliver","",0))

    assert SetService(session).validate_play_set(cards) is None

def test_valid_satterthquin_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Mr Satterthwaite","",2))
    cards.append(CardService(session).create_detective_card("Harley Quin","",0))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.SATTERTHQUIN

def test_valid_parker_pyne_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Parker Pyne","",2))
    cards.append(CardService(session).create_detective_card("Parker Pyne","",2))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.PARKER_PYNE

def test_invalid_parker_pyne_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Parker Pyne","",2))
    cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))

    assert SetService(session).validate_play_set(cards) is None

def test_valid_lady_eileen_brent_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Lady Eileen Brent","",2))
    cards.append(CardService(session).create_detective_card("Lady Eileen Brent","",2))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.LADY_EILEEN_BRENT

def test_invalid_lady_eileen_brent_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Lady Eileen Brent","",2))
    cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))

    assert SetService(session).validate_play_set(cards) is None

def test_valid_tommy_beresford_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))
    cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.TOMMY_BERESFORD

def test_invalid_tommy_beresford_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))
    cards.append(CardService(session).create_detective_card("Ariadne Oliver","",2))

    assert SetService(session).validate_play_set(cards) is None

def test_valid_tuppence_beresford_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Tuppence Beresford","",2))
    cards.append(CardService(session).create_detective_card("Tuppence Beresford","",2))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.TUPPENCE_BERESFORD

def test_invalid_tuppence_beresford_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Tuppence Beresford","",2))
    cards.append(CardService(session).create_event_card("Another Victim",""))

    

def test_valid_siblings_beresford_set(session: Session):
    cards = list()
    cards.append(CardService(session).create_detective_card("Tuppence Beresford","",2))
    cards.append(CardService(session).create_detective_card("Tommy Beresford","",2))

    assert SetService(session).validate_play_set(cards) == DetectiveSetType.SIBLINGS_BERESFORD
