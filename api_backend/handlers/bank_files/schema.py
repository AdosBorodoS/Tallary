import json
from pydantic import BaseModel, ConfigDict, Field
from datetime import date

class BaseTools(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self):
        return json.loads(self.model_dump_json(by_alias=True, exclude_unset=True))


class RegistryConstSchema(BaseTools):
    fileStorageDir:str|None = Field(default=None)
    

class CreateHandlerBankTransactions(BaseTools):
    userID:int = Field()
    fileName:str = Field()
    operationDate:date = Field()
    description:str|None = Field(default=None)
    currencyAmount:float = Field()

class AlfaHandlerUpdateData(BaseTools):
    operationDate:date | None = Field(default=None)
    postingDate:date | None = Field(default=None)
    code:str | None = Field(default=None)
    category:str | None = Field(default=None)
    description:str | None = Field(default=None)
    currencyAmount:float | None = Field(default=None)
    status:str | None = Field(default=None)

class TinkoffHandlerUpdateData(BaseTools):
    operationDate:date | None = Field(default=None)
    postingDate:date | None = Field(default=None)
    description:str | None = Field(default=None)
    description2:str | None = Field(default=None)
    currencyAmount:float | None = Field(default=None)
    amount:float | None = Field(default=None)

class CashHandlerUpdateData(BaseTools):
    operationDate:date | None = Field(default=None)
    category:str | None = Field(default=None)
    description:str | None = Field(default=None)
    currencyAmount:float | None = Field(default=None)
    status:str | None = Field(default=None)

class DeleteTransactionSchema(BaseTools):
    transactionID:int = Field()