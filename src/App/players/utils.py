from datetime import date
import random

from sqlalchemy.orm import Session
from App import players
from App.card.utils import db_card_2_card_info, db_card_2_card_private_info
from App.games.models import Game
from App.models import db
from App.play.schemas import CardsOffTheTableInfo, NotifierCardsOffTheTable
from App.players.enums import PlayerRole
from App.players.models import Player
from App.players.schemas import AllyInfo, CardsPlayedInfo, PlayerInfo, PlayerPlayedCardsInfo, PlayerPrivateInfo, PlayerPublicInfo
from App.secret.utils import db_secret_2_secret_private_info, db_secret_2_secret_public_info
from App.sets.utils import db_dset_2_set_public_info
from App.card.schemas import CardPublicInfo
from App.play.enums import ActionType
from App.sets.models import DetectiveSet


def db_player_2_player_info(db_player: Player) -> PlayerInfo:
    return PlayerInfo(
        playerId=db_player.id,
        playerName=db_player.name,
        birthDate=db_player.birthday
    )



def sort_players(players: list[Player]):
    target_date = date(1890, 9, 15)
    
    target_month, target_day = 9, 15  # 15 de septiembre
    
    def date_diff(player):
        
        player_month, player_day = player.birthday.month, player.birthday.day
        target = date(2000, target_month, target_day)
        player_date = date(2000, player_month, player_day)
        
        diff = abs((player_date - target).days)
        
        return min(diff, 365 - diff)
    
    players.sort(key=date_diff)
  
    min_diff = date_diff(players[0])
    
    closest_players = [player for player in players if date_diff(player) == min_diff]
    
    selected_player = random.choice(closest_players)
    
    remaining_players = [player for player in players if player != selected_player]
    random.shuffle(remaining_players)

    players = [selected_player] + remaining_players
    
    return players

def db_player_2_player_public_info(db_player: Player) -> PlayerPublicInfo:
    return PlayerPublicInfo(
        id=db_player.id,
        name=db_player.name,
        avatar=db_player.avatar,
        turnOrder=db_player.turn_order,
        turnStatus=db_player.turn_status.value,
        cardCount=len(db_player.cards),
        secrets=[db_secret_2_secret_public_info(secret) 
                for secret in db_player.secrets
            ],
        sets= [db_dset_2_set_public_info(dset) for dset in db_player.sets]
    )

def db_player_2_player_private_info(db_player: Player) -> PlayerPrivateInfo:

    ally = None

    if db_player.ally:
        
        if db_player.role == PlayerRole.MURDERER:
            allyRole = PlayerRole.ACCOMPLICE.value
        else:
            allyRole = PlayerRole.MURDERER.value

        ally = AllyInfo(
            id=db_player.ally,
            role=allyRole
        )
        
    return PlayerPrivateInfo(
        cards=[db_card_2_card_private_info(card) for card in db_player.cards],
        secrets=[db_secret_2_secret_private_info(secret) 
                for secret in db_player.secrets
            ],
        role=db_player.role.value,
        ally=ally
    )
    
def db_player_2_played_cards_played_info(
        db_player: Player,
        db_set: DetectiveSet,
        cards_played: list[int],
        action_type: ActionType

    ) -> CardsPlayedInfo:

        payload = PlayerPlayedCardsInfo(
            playerId = db_player.id,
            cards = [db_card_2_card_info(card) for card in db_set.cards if card.id in cards_played],
            actionType=action_type.value
        )

        return CardsPlayedInfo(payload=payload)
    
def db_player_cards_off_the_tables_info(
    db_player: Player,
    db_player_selected: Player,
    not_so_fast: int
) -> NotifierCardsOffTheTable:

    payload = CardsOffTheTableInfo(
        playerId = db_player.id,
        quantity = not_so_fast,
        selectedPlayerId = db_player_selected.id
    )

    return NotifierCardsOffTheTable(payload=payload)