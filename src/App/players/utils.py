from datetime import date
import random
from App import players
from App.players.models import Player
from App.players.schemas import PlayerInfo


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