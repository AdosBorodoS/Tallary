from typing import Dict
from fastapi import HTTPException, status
from abc import ABC, abstractmethod

from ...handlers.friends.friends_handler import FriendsCatalogHandler
# from ...handlers.db.orm_models.abstract_models import AbstractFriendsCatalog
from ...handlers.logers.loger_handlers import LogerHandler
from .schema import AddFriend,DeleteFriend
from ..users.schama import AuthUser

class AbstractFriendsService(ABC):
    @abstractmethod
    def __init__(self, logerHandler, friendsCatalogHandler):
        super().__init__()
        self.logerHandler:LogerHandler = logerHandler
        self.friendsCatalogHandler:FriendsCatalogHandler = friendsCatalogHandler

    @abstractmethod
    def add_friend(self, userID:int, friendID:int):
        pass

    @abstractmethod
    def get_friend(self, userID:int):
        pass

    @abstractmethod
    def delete_friend(self, userID:int, nofriendID:int):
        pass

class FriendsService(AbstractFriendsService):
    def __init__(self, logerHandler, friendsCatalogHandler):
        super().__init__(logerHandler, friendsCatalogHandler)

    async def _user_is_exist(self, userID:int):
        userFilter = (self.friendsCatalogHandler.userCatalogHandler.dbt.id == userID,)
        userData = await self.friendsCatalogHandler.userCatalogHandler.get_data(userFilter)
        if userData.__len__() == 1:
            return True
        elif userData.__len__() == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User doesn't exist")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="More then 1 user exist")

    async def _user_is_friend(self, userID:int, friendID:int):
        columnFilters=(
            self.friendsCatalogHandler.dbt.userID == userID,
            self.friendsCatalogHandler.dbt.friendID == friendID
        )
        usersData = await self.friendsCatalogHandler.get_friend(columnFilters)
        if usersData.__len__() == 1:
            return True
        elif usersData.__len__() == 0:
            return False
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Friend add more the 1 times")

    async def add_friend(self, authUser:AuthUser, addData:AddFriend):
        if await self._user_is_exist(addData.friendID) and not await self._user_is_friend(authUser.get('id'),addData.friendID):
            addResponse = await self.friendsCatalogHandler.add_friend(userID=authUser.get('id'), friendID=addData.friendID)
            if addResponse.__len__() > 1:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Add more the 1 friend")
            addFriendFielter = (
                self.friendsCatalogHandler.userCatalogHandler.dbt.id == addResponse[0].get("friendID"),
            )
            addFriendData = await self.friendsCatalogHandler.userCatalogHandler.get_data(addFriendFielter)
            addFriendData = [x.to_dict() for x in addFriendData]
            [x.pop("password") for x in addFriendData]
            return addFriendData
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Friend already exist")

    async def get_friend(self, authUser:AuthUser) -> Dict:
        columnFilters = (self.friendsCatalogHandler.dbt.userID == authUser.get('id'),)
        getDataResponse = await self.friendsCatalogHandler.get_friend(columnFilters)

        getUsersFiletr = (
            self.friendsCatalogHandler.userCatalogHandler.dbt.id.in_(
            [x.to_dict().get("friendID") for x in getDataResponse]),
            )
        friendsCatalog = await self.friendsCatalogHandler.userCatalogHandler.get_data(getUsersFiletr)
        friendsCatalog = [x.to_dict() for x in friendsCatalog]
        [x.pop("password") for x in friendsCatalog]
        
        return friendsCatalog

    async def delete_friend(self, authUser:AuthUser, deleteData:DeleteFriend):
        if await self._user_is_exist(deleteData.friendID) and await self._user_is_friend(authUser.get('id'), deleteData.friendID):
            deleteResponse = await self.friendsCatalogHandler.delete_friend(userID=authUser.get('id'), nofriendID=deleteData.friendID)            
            return deleteResponse
        
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User isn't friend")
