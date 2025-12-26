import json
from pydantic import BaseModel, Field, ConfigDict

class BaseTools(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self):
        return json.loads(self.model_dump_json(by_alias=True, exclude_unset=True))


class AddCategoryCatalogSchema(BaseTools):
    userID: int = Field()
    categoryName: str = Field()

class UpdateDataCatalogSchema(BaseTools):
    categoryID: int = Field()
    categoryName: str = Field()


class AddCategoryConditionsSchema(BaseTools):
    categoryID: int = Field()
    conditionValue: str = Field()
    isExact:bool = Field()

class DeleteCategoryConditionsSchema(BaseTools):
    conditionID:int = Field()

class UpdateDataConditionsSchema(BaseTools):
    conditionID: int = Field()
    conditionValue: str = Field()
    isExact:bool = Field()