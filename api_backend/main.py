from typing import Optional, List
from fastapi import FastAPI, Depends, UploadFile, File

from .services.users.schama import CreateUser
from .services.load_bank_file_service.schema import CreateServiceBankTransactions,SearchParametrs

from .handlers.users.schema import UpdateUser
from .handlers.bank_files.schema import TinkoffHandlerUpdateData, AlfaHandlerUpdateData
from .services.friends.schema import AddFriend, DeleteFriend
from .services.goals.schema import CreatGoal, CreatColabGoal, AddGoalOwner, CreatGoalOperators

from .initialization import (userService, 
                             bankService, 
                             friendsService, 
                             goalsService)


app = FastAPI(
    title="Tallary's api getaway",
    description="API Tallary",
    version="0.0.1 Alpha",
    servers=[
        {"url": "http://127.0.0.1:8000", "description": "Development Server"}
    ]
)

# Users

@app.get('/login', tags=['User'])
async def login(authUser = Depends(userService.auth_user)):
    singInResponse = await userService.login(authUser.get('userName'), authUser.get('password'))
    return singInResponse

@app.get('/user', tags=['User'])
async def get_users(queryUserName:Optional[str] = '', authUser = Depends(userService.auth_user)):
    getResponse = await userService.get_users(queryUserName)
    return getResponse

@app.post('/user', tags=['User'])
async def create_user(userData:CreateUser):
    createResponse = await userService.create_user(userData)
    return createResponse

@app.patch('/user', tags=['User'])
async def update_user(updateData:UpdateUser, authUser = Depends(userService.auth_user)):
    updateResponse = await userService.update_user(authUser,updateData)
    return updateResponse

@app.delete('/user', tags=['User'])
async def delete_user(authUser = Depends(userService.auth_user)):
    deleteResponse = await userService.delete_user(authUser)
    return deleteResponse


# Bank transactions

@app.get('/bank_transactions', tags=['Bank transactions'])
async def get_bank_transactions(slug:str, getFiletr: SearchParametrs = Depends(), authUser = Depends(userService.auth_user)):
    insertedData = await bankService.get_bank_transactions(authUser,slug,getFiletr)
    return insertedData

@app.post('/bank_transactions', tags=['Bank transactions'])
async def create_bank_transactions(dto:CreateServiceBankTransactions, slug:str, authUser = Depends(userService.auth_user)):
    insertedData = await bankService.create_bank_transactions(authUser,slug,dto)
    return insertedData

@app.post('/bank_transactions/file', tags=['Bank transactions'])
async def create_bank_transactions_by_load_file(slug:str, file: UploadFile = File(...), authUser = Depends(userService.auth_user)):
    insertFileResponse = await bankService.create_bank_transactions_by_load_file(authUser, slug, file)
    return insertFileResponse

@app.patch('/bank_transactions', tags=['Bank transactions'])
async def update_bank_transactions(transactionID: int, slug:str, updateData: TinkoffHandlerUpdateData | AlfaHandlerUpdateData, authUser = Depends(userService.auth_user)):
    updatedResponse = await bankService.update_bank_transactions(authUser, transactionID, slug, updateData)
    return updatedResponse

@app.delete('/bank_transactions', tags=['Bank transactions'])
async def delete_bank_transactions(slug:str, deleteFiletr: SearchParametrs = Depends(), authUser = Depends(userService.auth_user)):
    insertedData = await bankService.delete_bank_transactions(authUser, slug, deleteFiletr)
    return insertedData

# Friends

@app.get('/friend', tags=['Friends'])
async def get_friends(authUser = Depends(userService.auth_user)):
    return await friendsService.get_friend(authUser=authUser)

@app.post('/friend', tags=['Friends'])
async def add_friend(addData: AddFriend, authUser = Depends(userService.auth_user)):
    return await friendsService.add_friend(authUser=authUser, addData=addData)

@app.delete('/friend', tags=['Friends'])
async def delete_friend(deleteData:DeleteFriend, authUser = Depends(userService.auth_user)):
    return await friendsService.delete_friend(authUser=authUser, deleteData=deleteData)

# Goals

@app.post('/goals/create', tags=['Goals'])
async def create_goal(createGoalData:CreatGoal, authUser = Depends(userService.auth_user)):
    return await goalsService.create_goal(ceateGoalData=createGoalData, userAuth=authUser)

@app.post('/goals/colab/create', tags=['Goals'])
async def create_goal(ceateColabGoalData:CreatColabGoal, authUser = Depends(userService.auth_user)):
    return await goalsService.create_colab_goal(ceateColabGoalData=ceateColabGoalData, userAuth=authUser)

@app.post('/goals/owner', tags=['Goals'])
async def add_owner_goal(addGoalOwnerData: AddGoalOwner, authUser = Depends(userService.auth_user)):
    return await goalsService.add_goal_owner(authUser, addGoalOwnerData)

@app.post('/goals/operators', tags=['Goals'])
async def add_operators_goal(goalID: int, operators: List[CreatGoalOperators], authUser = Depends(userService.auth_user)):
    return await goalsService.add_goal_operator(goalID, operators)

@app.get('/goals/get_goals_catalog', tags=['Goals'])
async def get_goals(authUser = Depends(userService.auth_user)):
    return await goalsService.get_goals(authUser)

@app.delete('/goals/owner', tags=['Goals'])
async def delete_goal_owner(goalID: int,authUser = Depends(userService.auth_user)):
    return await goalsService.delete_goal_owner(authUser, goalID)

@app.delete('/goals/operators', tags=['Goals'])
async def delete_goal_operators(goalRuleID: int,authUser = Depends(userService.auth_user)):
    return await goalsService.delete_goal_operator(goalRuleID)

@app.delete('/goals/goal', tags=['Goals'])
async def delete_goal(goalID: int,authUser = Depends(userService.auth_user)):
    return await goalsService.delete_goal_owner(goalID)
