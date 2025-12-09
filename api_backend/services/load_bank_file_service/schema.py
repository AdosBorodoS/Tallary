import json
from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class BaseTools(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self) -> dict:
        return json.loads(self.model_dump_json(by_alias=True, exclude_unset=True))


class CreateServiceBankTransactions(BaseTools):
    operationDate:date = Field()
    description:str|None = Field(default=None)
    currencyAmount:float = Field()

class CreateFileServiceBankTransactions(BaseTools):
    slug:str = Field(description="BankHandlerRegistry slug name")
    fileType:str = Field()
    
class SearchParametrs(BaseTools):
    eq_operationDate: date | None = Field(default=None, description='Дата поиска. Все что равно заданной даты операции')
    ge_operationDate: date | None = Field(default=None, description='Дата поиска. Все что больше заданной даты операции')
    le_operationDate: date | None = Field(default=None, description='Дата поиска. Все что меньше заданной даты операции')

    like_description: str | None = Field(default=None, description='Поиск по вхождуению описания')

    ge_currencyAmount: float | None = Field(default=None, description='операция на сумму больше чем указаное хчисло')
    le_currencyAmount: float | None = Field(default=None, description='операция на сумму меньше чем указаное хчисло')

