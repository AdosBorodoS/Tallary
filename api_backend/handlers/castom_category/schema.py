from pydantic import BaseModel, Field

class AddCategorySchema(BaseModel):
    userID: int = Field()
    categoryName: str = Field()
    isExact:bool = Field()

class UpdateDataSchema(BaseModel):
    categoryID: int = Field()
    categoryName: str = Field()
    isExact:bool = Field()