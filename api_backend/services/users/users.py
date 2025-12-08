from fastapi import Depends, HTTPException, status

# from pydantic import BaseModel
from abc import ABC, abstractmethod

# from ...handlers.users.schema import UpdateUser
from ...services.users.schama import AuthUser
from ...handlers.users.user import UserHandler
from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.users.schema import UpdateUser
from .schama import CreateUser, AuthUser

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

    async def auth_user(self, auth: AuthUser = Depends(AuthUser.from_headers)) -> dict:
        filter_ = (
            self.userHandler.dbt.userName == auth.userName,
            self.userHandler.dbt.password == auth.password,
        )
        data = await self.userHandler.get_data(columnFilters = filter_)
        dataLenth = data.__len__()
        
        if dataLenth == 1:
            return [x.to_dict() for x in data][0]
        elif dataLenth > 1:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="INTERNAL SERVER ERROR. More then 1 users")
        elif dataLenth == 0:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"desc":"FORBIDDEN"})
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="INTERNAL SERVER ERROR")
    
    async def get_users(self, userName:str):
        getFilter = (
            self.userHandler.dbt.userName.like(f'%{userName}%'),
        )
        gotData = await self.userHandler.get_data(getFilter)
        return {"data":gotData}
        
    async def _is_exist_user_name(self, userName:str) -> bool:
        userNameFilter = (self.userHandler.dbt.userName == userName,)
        usersList = await self.userHandler.get_data(userNameFilter)
        if usersList.__len__():
            return True
        return False

    async def create_user(self, createData:CreateUser):
        if not await self._is_exist_user_name(createData.userName):
            createdUser = await self.userHandler.insert_data(userName=createData.userName, password=createData.password)
            return {"msg": "User created", "userName": createdUser[0].get('userName')} # st: 200 
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exist")
        
    async def update_user(self, authUser:AuthUser, updateData:UpdateUser):
        if not await self._is_exist_user_name(updateData.userName):
            updatedUser = await self.userHandler.update_data(userID=authUser.get("id",-1), updatesData=updateData)
        return {"msg": "User updated","userName":updatedUser.to_dict().get('userName')} # st: 200

    async def delete_user(self, authUser:AuthUser,):
        deletedUser = await self.userHandler.delete_data(userID=authUser.get("id",-1))
        if deletedUser:
            return {"msg":"User deleted", "userName":authUser.get("userName","No useranme")} # st: 200
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")