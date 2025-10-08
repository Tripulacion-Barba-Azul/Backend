

from App.secret.models import Secret
from App.secret.schemas import SecretPublicInfo




def db_secret_2_secret_public_info(db_secret: Secret) -> SecretPublicInfo:
    return SecretPublicInfo(
        id=db_secret.id,
        revealed=db_secret.revealed,
        name=db_secret.name
    )   