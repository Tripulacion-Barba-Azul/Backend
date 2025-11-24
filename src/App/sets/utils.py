from src.App.sets.models import DetectiveSet
from src.App.sets.schemas import SetPublicInfo
from src.App.card.utils import db_card_2_card_info


def db_dset_2_set_public_info(db_dset: DetectiveSet) -> SetPublicInfo:
    return SetPublicInfo(
        setId=db_dset.id,
        setName=db_dset.type.value,
        cards = [db_card_2_card_info(card) for card in db_dset.cards]
        

    )
