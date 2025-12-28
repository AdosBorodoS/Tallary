from typing import List
from pydantic import BaseModel, Field


class AddConditionValues(BaseModel):
    conditionValue: str = Field()
    isExact:bool = Field()

class AddCategoryServiceSchema(BaseModel):
    categoryName: str = Field()
    conditionValues: List[AddConditionValues]


class UpdateConditionValues(BaseModel):
    conditionID: int = Field()
    conditionValue: str = Field()
    isExact:bool = Field()

class UpdateDataServiceSchema(BaseModel):
    categoryName: str | None = Field(default=None)
    conditionValues: List[UpdateConditionValues] | None  = Field(default=None)
