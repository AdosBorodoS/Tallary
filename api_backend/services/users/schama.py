from pydantic import BaseModel, Field

class AuthUser(BaseModel):
    userName:str = Field()
    password:str = Field() 