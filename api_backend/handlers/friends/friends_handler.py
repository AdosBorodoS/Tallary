from typing import List
from abc import ABC, abstractmethod
from fastapi import HTTPException, status

from ..users.user import AbstractUserHandler
from ..logers.loger_handlers import LogerHandler
from ..db.db_handlers import AbstractDataBaseHandler
from ..db.orm_models.abstract_models import AbstractFriendsCatalog


class AbstractFriendsCatalogHandler(ABC):
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


class FriendsCatalogHandler(AbstractFriendsCatalogHandler):
    def __init__(self, logerHandler, userCatalogHandler, dbHandler, dbt):
        super().__init__(logerHandler, userCatalogHandler, dbHandler, dbt)

    async def add_friend(self, userID:int, friendID:int):
        return await self.dbHandler.insert_data(data=(self.dbt(userID=userID,friendID=friendID),))

    async def _user_is_exist(self, userID:int):
        userFilter = (self.userCatalogHandler.dbt.id == userID,)
        userData = await self.userCatalogHandler.get_data(userFilter)
        if userData.__len__() == 1:
            return True
        elif userData.__len__() == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User doesn't exist")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="More then 1 user exist")

    async def _user_is_friend(self, userID:int, friendID:int):
        
        if userID == friendID:return True
        
        columnFilters=(
            self.dbt.userID == userID,
            self.dbt.friendID == friendID
        )
        usersData = await self.get_friend(columnFilters)
        if usersData.__len__() == 1:
            return True
        elif usersData.__len__() == 0:
            return False
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Friend add more the 1 times")

    async def get_friend(self, columnFilters:List):
        return await self.dbHandler.get_table_data([self.dbt], columnFilters)

    async def delete_friend(self, userID:int, nofriendID:int):
        deleteFilter = (self.dbt.userID == userID, self.dbt.friendID == nofriendID)
        return await self.dbHandler.delete_data(self.dbt, deleteFilter)
