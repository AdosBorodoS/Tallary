from abc import ABC, abstractmethod
from typing import List
from ..logers.loger_handlers import LogerHandler
from ..db.db_handlers import AbstractDataBaseHandler
from ..db.orm_models.abstract_models import AbstractGoalsOwnersCatalog

class AbstractGoalOwnersCatalogHandler(ABC):
    @abstractmethod
    def __init__(self, logerHandler, dbt, dbHandler):
        super().__init__()
        self.logerHandler:LogerHandler = logerHandler
        self.dbHandler:AbstractDataBaseHandler = dbHandler
        self.dbt:AbstractGoalsOwnersCatalog = dbt

    @abstractmethod
    def get_data(self, columnFilters:List):
        pass
    
    @abstractmethod
    def insert_data(self, userID:int, goalID:int):
        pass
    
    @abstractmethod
    def delete_data(self, userID:int, goalID:int):
        pass


class GoalOwnersCatalogHandler(AbstractGoalOwnersCatalogHandler):
    def __init__(self, logerHandler, dbt, dbHandler):
        super().__init__(logerHandler, dbt, dbHandler)

    async def get_data(self, columnFilters:List):
        return await self.dbHandler.get_table_data([self.dbt], columnFilters)
    
    async def insert_data(self, userID:int, goalID:int):
        return await self.dbHandler.insert_data(data=(self.dbt(userID=userID,goalID=goalID),))
    
    async def delete_data(self, userID:int, goalID:int):
        return await self.dbHandler.delete_data(self.dbt, (self.dbt.userID == userID, self.dbt.goalID == goalID,))
        
