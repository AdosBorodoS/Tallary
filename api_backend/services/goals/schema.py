from typing import List
from pydantic import BaseModel, Field


class ParticipantCatalog(BaseModel):
    userID:int = Field()


class GaolParticipant(BaseModel):
    goalID:int = Field()
    participants:List[ParticipantCatalog] = Field()

class CreatGoalOperators(BaseModel):
    goalOperator:str = Field(description="Оператор типа Operations")
    goalRule:int = Field(description="Суммацели")

class CreatGoal(BaseModel):
    goalName:str = Field(description="Название цели")
    operators:List[CreatGoalOperators] = Field(description="Список операторов цели")

class CreatColabGoal(BaseModel):
    friendIDs:List[int] = Field(description="ID друзей кто учавствует в цели")
    goalName:str = Field(description="Название цели")
    operators:List[CreatGoalOperators] = Field(description="Список операторов цели")

class AddGoalOwner(BaseModel):
    goalID:int = Field()
    friendIDs:List[int] = Field(description="ID друзей кто учавствует в цели")
