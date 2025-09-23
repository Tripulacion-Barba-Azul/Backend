from pydantic import BaseModel, root_validator

class SecretDTO(BaseModel):
    name:str
    description: str
    assanssin:bool
    acomplice:bool


    @root_validator
    def check_assasin_acomplice (cls,values):
        is_assassin = values.get('assassin')
        is_acomplice = values.get('acomplice')
        if(is_assassin & is_acomplice):
           raise ValueError("El asesino y el complice no pueden ser el mismo jugador")
        return values
        