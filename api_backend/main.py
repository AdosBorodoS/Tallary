from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File

from .services.users.schama import CreateUser
from .services.load_bank_file_service.schema import CreateServiceBankTransactions,SearchParametrs

from .handlers.users.schema import UpdateUser
from .handlers.bank_files.schema import TinkoffHandlerUpdateData, AlfaHandlerUpdateData

from .initialization import userService, bankService



app = FastAPI(
    title="Tallary's api getaway",
    description="API Tallary",
    version="0.0.1 Alpha",
    servers=[
        {"url": "http://127.0.0.1:8000", "description": "Development Server"}
    ]
)

# Users

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
async def delete_bank_transactions(authUser = Depends(userService.auth_user)):
    return {"status":201}


