import secrets
from sqlalchemy.orm import Session

from App.secret.models import Secret
from App.games.models import Game
from App.games.models import Player
from App.secret.enums import SecretType
import random

generic_secrets=[
    ("Prankster","I make calls to the police to acuse my friends of murder",
      SecretType.GENERIC),
    ("Just a Fantasy", "I made poems about murdering my friend",
      SecretType.GENERIC),
    ("Untouched", "I've never been kissed. Ever",
      SecretType.GENERIC),
    ("Secret Hate", "I have an intense dislike for everyone i work and live with",
      SecretType.GENERIC),
    ("Faked Dead", "I Fake my own dead",
      SecretType.GENERIC),
    ("Impostor", "I escaped my old life and change my identity",
      SecretType.GENERIC),
    ("Gambling Problem", "I am the worst gambler in the world",
      SecretType.GENERIC)  
]

assassin_secret = ("You are the murderer",
                   "If this card is revealed, you are caugth and lost the game",
                    SecretType.MURDERER)

accomplice_secret = ("You are the accomplice",
                     "If the Murderer escapes, you both win the game"
                     " even if this card is revealed",
                     SecretType.ACCOMPLICE )



def get_secret(secret_id, db:Session):
    secret = db.query(Secret).filter_by(id = secret_id).first()
    if not secret:
         raise ValueError(
            f"Secret with id:{secret_id} dont exist"
        )
    else:
        return secret


def create_secret(new_name, new_description, new_type):
    new_secret = Secret(
                        name = new_name,
                        description = new_description,
                        type = new_type,
                        revealed = False
                        )
    
    return new_secret




def reveal_secret(secret, db:Session):

    secret.revealed = True
    db.commit()
    db.refresh(secret)

def relate_secret_player(player, secret, db:Session, commit=False):

    player.secrets.append(secret)

    if commit:
        db.commit()
        db.refresh(player)
        db.refresh(secret)

def unrelate_secret_player(player, secret, db:Session, commit=False):

    player.secrets.remove(secret)

    if commit:
        db.commit()
        db.refresh(player)
        db.refresh(secret)

def create_and_draw_secrets(game_id, db:Session):

    game = db.query(Game).filter_by(id = game_id).first()
    players = game.players
    secret_list = list()


    if len(players) < 5:
        for i in range (3*len(players) - 1):
            random_secret = random.choice(generic_secrets)
            new_secret = create_secret(
                                random_secret[0],
                                random_secret[1],
                                random_secret[2]
                                )
            secret_list.append(new_secret)
        asn_secret = create_secret(
                                assassin_secret[0],
                                assassin_secret[1],
                                assassin_secret[2]
                                )
        secret_list.append(asn_secret)
    else:
        for i in range (3*len(players) - 2):
            random_secret = random.choice(generic_secrets)
            new_secret = create_secret(
                        random_secret[0],
                        random_secret[1],
                        random_secret[2]
                        )
            secret_list.append(new_secret)
        asn_secret = create_secret(
                                assassin_secret[0],
                                assassin_secret[1],
                                assassin_secret[2]
                                )
        secret_list.append(asn_secret)
        acm_secret =create_secret(
                                accomplice_secret[0],
                                accomplice_secret[1],
                                accomplice_secret[2]
                        
                                )
        secret_list.append(acm_secret)


    # mezclar la lista antes de añadir a la sesión para que los ids no sigan el orden de creación
    random.shuffle(secret_list)

    # añadir todos los secretos a la sesión en el orden aleatorio y persistir una sola vez
    for s in secret_list:
        db.add(s)
    db.commit()

    # refrescar para obtener ids asignados por la BD
    for secret in secret_list:
        db.refresh(secret)


    secret_list_copy = secret_list.copy()

    random.shuffle(secret_list_copy)
    for i in range (3):
        for player in players:
                secret = secret_list_copy[0]
                if secret.name == "You are the accomplice" and asn_secret in player.secrets:
                    secret = secret_list_copy[1]

                relate_secret_player(player, secret, db, commit=False)
                secret_list_copy.remove(secret)   
            
    db.commit()
    for secret in secret_list:
            db.refresh(secret)