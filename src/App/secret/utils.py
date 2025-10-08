

from App.secret.models import Secret
from App.secret.schemas import SecretPrivateInfo, SecretPublicInfo




def db_secret_2_secret_public_info(db_secret: Secret) -> SecretPublicInfo:
    return SecretPublicInfo(
        id=db_secret.id,
        revealed=db_secret.revealed,
        name= db_secret.name if db_secret.revealed else None
    )

def db_secret_2_secret_private_info(db_secret: Secret) -> SecretPrivateInfo:
    return SecretPrivateInfo(
        id=db_secret.id,
        name=db_secret.name,
        revealed=db_secret.revealed
    )