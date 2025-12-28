import json
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

class BaseTools(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self):
        return json.loads(self.model_dump_json(by_alias=True, exclude_unset=True))

class UpdateUser(BaseTools):
    userName:str | None = Field(default=None)
    password:str | None = Field(default=None)

