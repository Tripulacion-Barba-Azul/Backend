from App.card.models import Card
from App.card.schemas import CardPublicInfo


def db_card_2_card_info(db_card: Card)-> CardPublicInfo:
    return CardPublicInfo(
        id=db_card.id,
        name=db_card.name
    )   