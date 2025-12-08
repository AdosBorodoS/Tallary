from typing import Optional
from fastapi import FastAPI, Depends

from .services.users.schama import CreateUser
from .handlers.users.schema import UpdateUser
from .initialization import userService

app = FastAPI(
    title="Tallary's api getaway",
    description="API Tallary",
    version="0.0.1 Alpha",
    servers=[
        {"url": "http://127.0.0.1:8000", "description": "Development Server"}
    ]
)



@app.get('/user', tags=['User'])
async def get_users(queryUserName:Optional[str] = '',authUser = Depends(userService.auth_user)):
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
