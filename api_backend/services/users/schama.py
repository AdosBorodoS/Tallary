from pydantic import BaseModel, Field
from fastapi import Header

class AuthUser(BaseModel):
    userName:str = Field()
    password:str = Field() 

    @classmethod
    def from_headers(cls,username:str = Header(..., alias="X-Username"), password:str = Header(..., alias="X-Password")) -> "AuthUser":
        return cls(userName=username, password=password)

class CreateUser(BaseModel):
    userName:str = Field()
    password:str = Field() 