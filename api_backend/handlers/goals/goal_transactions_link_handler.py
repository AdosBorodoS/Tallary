import json
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime, date
from abc import ABC, abstractmethod
from sqlalchemy import types as satypes
from typing import Any, Dict, Mapping, Tuple, List
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .schema import UpdateGoalCatalog
from ..logers.loger_handlers import LogerHandler
from ..db.db_handlers import AbstractDataBaseHandler
from ..db.orm_models.abstract_models import AbstractGoalTransactionLink

class AbstractGoalsTransactionLinkHandler(ABC):
    @abstractmethod
    def __init__(self, logerHandler, dbHandler, dbt):
        super().__init__()
        self.dbt:AbstractGoalTransactionLink = dbt 
        self.logerHandler:LogerHandler = logerHandler
        self.dbHandler:AbstractDataBaseHandler = dbHandler

    @abstractmethod
    def get_data(self, columnFilters:List):
        pass
    
    @abstractmethod
    def insert_data(self, goalID:int, transactionID:int, transactionSource:str, contributorUserID:int):
        pass
    
    @abstractmethod
    def delete_data(self, deleteFilter:List):
        pass

class GoalsTransactionLinkHandler(AbstractGoalsTransactionLinkHandler):
    def __init__(self, logerHandler, dbHandler, dbt):
        super().__init__(logerHandler, dbHandler, dbt)

    async def get_data(self, columnFilters:List):
        return await self.dbHandler.get_table_data([self.dbt], columnFilters)

    async def insert_data(self, goalID:int, transactionID:int, transactionSource:str, contributorUserID:int):
        return await self.dbHandler.insert_data(data=(self.dbt(
                    goalID = goalID,
                    transactionID = transactionID,
                    transactionSource = transactionSource,
                    contributorUserID = contributorUserID
        ),))
    
    async def delete_data(self, deleteFilter:List):
        return await self.dbHandler.delete_data(self.dbt, deleteFilter)