from abc import ABC, abstractmethod
from typing import List
from ..users.user import AbstractUserHandler
from ..logers.loger_handlers import LogerHandler
from ..db.db_handlers import AbstractDataBaseHandler
from ..db.orm_models.abstract_models import AbstractFriendsCatalog


class AbcstractFriendsCatalogHandler(ABC):
    @abstractmethod
    def __init__(self, logerHandler, userCatalogHandler, dbHandler, dbt):
        super().__init__()
        self.logerHandler:LogerHandler = logerHandler
        self.userCatalogHandler: AbstractUserHandler = userCatalogHandler
        self.dbHandler:AbstractDataBaseHandler = dbHandler
        self.dbt:AbstractFriendsCatalog = dbt 

    @abstractmethod
    def add_friend(self, userID:int, friendID:int):
        pass

    @abstractmethod
    def get_friend(self, userID:int):
        pass

    @abstractmethod
    def delete_friend(self, userID:int, nofriendID:int):
        pass


class FriendsCatalogHandler(AbcstractFriendsCatalogHandler):
    def __init__(self, logerHandler, userCatalogHandler, dbHandler, dbt):
        super().__init__(logerHandler, userCatalogHandler, dbHandler, dbt)

    async def add_friend(self, userID:int, friendID:int):
        return await self.dbHandler.insert_data(data=(self.dbt(userID=userID,friendID=friendID),))

    async def get_friend(self, columnFilters:List):
        return await self.dbHandler.get_table_data([self.dbt], columnFilters)

    async def delete_friend(self, userID:int, nofriendID:int):
        deleteFilter = (self.dbt.userID == userID, self.dbt.friendID == nofriendID)
        return await self.dbHandler.delete_data(self.dbt, deleteFilter)
