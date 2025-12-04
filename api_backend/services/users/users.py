from fastapi import Depends
# from pydantic import BaseModel
from abc import ABC, abstractmethod

# from ...handlers.users.schema import UpdateUser
from ...services.users.schama import AuthUser
from ...handlers.users.user import UserHandler
from ...handlers.logers.loger_handlers import LogerHandler

class AbstractUserService(ABC):
    
    @abstractmethod
    def __init__(self, logerHandler, userHandler):
        super().__init__()
        self.logerHandler:LogerHandler = logerHandler
        self.userHandler: UserHandler = userHandler

    @abstractmethod
    def auth_user(self):
        pass
        
    @abstractmethod
    def get_users(self):
        pass
    
    @abstractmethod
    def create_user(self):
        pass

    @abstractmethod
    def update_user(self):
        pass

    @abstractmethod
    def delete_user(self):
        pass

class UserService(AbstractUserService):
    
    def __init__(self, logerHandler, userHandler):
        super().__init__(logerHandler, userHandler)

    async def auth_user(self, auth:AuthUser = Depends()):
        filter_ = (
            self.userHandler.dbt.userName == auth.userName,
            self.userHandler.dbt.password == auth.password,
        )
        data = await self.userHandler.get_data(columnFilters = filter_)
        dataLenth = data.__len__()
        
        if dataLenth == 1:
            return auth
        elif dataLenth > 1:
            return {"error":400, "desc":"more then 1 user"}
        elif dataLenth == 0:
            return {"error":400, "desc":"No user"}
        else:
            raise
    
    async def get_users(self):
        return {"status":201}
        
    async def create_user(self):
        return {"status":201}

    async def update_user(self):
        return {"status":201}

    async def delete_user(self):
        return {"status":201}