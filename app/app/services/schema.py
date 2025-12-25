import json
from typing import Literal, List
from datetime import date
from pydantic import BaseModel, Field, ConfigDict


class ApiQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    def to_query(self) -> str:
        queryLine = '&'.join([f"{k}={v}" for k, v in self.model_dump(
            by_alias=True, exclude_unset=True).items()])
        if queryLine.__len__():
            return '?' + queryLine
        return ''

#  users
class GetUsersQuery(ApiQuery):
    queryUserName: str | None = Field(default=None)


# Bank
class GetBankTransactionsQuery(ApiQuery):
    slug: str = Field()
    eq_operationDate: str | None = Field(default=None)
    ge_operationDate: str | None = Field(default=None)
    le_operationDate: str | None = Field(default=None)
    like_description: str | None = Field(default=None)
    ge_currencyAmount: str | None = Field(default=None)
    le_currencyAmount: str | None = Field(default=None)

class PostBankTransactionsQuery(ApiQuery):
    slug: str = Field()

class PatchBankTransactionsQuery(ApiQuery):
    slug: str = Field()
    transactionID:int = Field() 

class DeleteBankTransactionsQuery(ApiQuery):
    slug: str = Field()
    transactionID:int = Field() 


class DeleteGoalQuery(ApiQuery):
    goalID:int = Field()

class PostGoalOperatorsQuery(ApiQuery):
    goalID:int = Field()

class DeleteGoalOperatorQuery(ApiQuery):
    operatorID:int = Field()


class DeleteCategoryQuery(ApiQuery):
    categoryID:int = Field()

class PatchCategoryQuery(ApiQuery):
    categoryID:int = Field()

class GetCategoryTransactionsQeury(ApiQuery):
    slugs:str = Field()


class GetAnalyticsCashFlow(ApiQuery):
    period:Literal["day", "month", "year"] = Field()

class GetAnalyticsLastTransactions(ApiQuery):
    limit:int = Field()


class GetUserLoadedFiles(ApiQuery):
    slugs:str = Field()



class ApiPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self):
        return json.loads(self.model_dump_json(by_alias=True, exclude_unset=True))

# Users
class UpdateUser(ApiPayload):
   userName:str|None = Field(default=None)
   password:str|None = Field(default=None)


# Bank
class PostBankTransactionsManualLoadPayload(ApiPayload):
    operationDate: date = Field()
    description: str|None = Field(default=None)
    currencyAmount: float = Field()

class PatchBankTransactionsManualLoadPayload(ApiPayload):
    operationDate: date = Field()
    postingDate: date| None = Field(default=None)
    description: str = Field()
    description2: str | None = Field(default=None)
    currencyAmount: float = Field()
    amount: float|None = Field(default=None)


class PostFriendPayload(ApiPayload):
    friendID:int = Field()

class DeleteFriendPayload(ApiPayload):
    friendID:int = Field()




class GoalOperator(ApiPayload):    
    goalOperator:str = Field()
    goalRule:int = Field()

class AddGoalPayload(ApiPayload):
    goalName:str = Field() 
    operators:List[GoalOperator]



class ParticipantCatalog(ApiPayload):
    userID:int = Field()

class GaolParticipant(ApiPayload):
    goalID:int = Field()
    participants:List[ParticipantCatalog] = Field()

class PostGoalOperatorsPayload(ApiPayload):
    goalOperator:str = Field()
    goalRule:int = Field()

class AddConditionValues(ApiPayload):
    conditionValue: str = Field()
    isExact:bool = Field()

class AddCategoryPayload(ApiPayload):
    categoryName: str = Field()
    conditionValues: List[AddConditionValues]

class UpdateConditionValues(ApiPayload):
    conditionID: int = Field()
    conditionValue: str = Field()
    isExact:bool = Field()

class UpdateDataServiceSchemaPayLoad(ApiPayload):
    categoryName: str | None = Field(default=None)
    conditionValues: List[UpdateConditionValues] | None  = Field(default=None)

