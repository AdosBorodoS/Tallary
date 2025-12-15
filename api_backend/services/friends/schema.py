from pydantic import BaseModel, Field

class AddFriend(BaseModel):
    friendID:int = Field()

class DeleteFriend(BaseModel):
    friendID:int = Field()