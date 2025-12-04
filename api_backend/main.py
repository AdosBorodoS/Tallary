from fastapi import FastAPI, Depends

from .initialization import userService
# from .websocket_handlers.websocket_handler import WSManager

app = FastAPI(
    title="Tallary's api getaway",
    description="API Tallary",
    version="0.0.1 Alpha",
    servers=[
        {"url": "http://127.0.0.1:8000", "description": "Development Server"}
    ]
)



@app.get('/user', tags=['User'])
async def get_users(authUser = Depends(userService.auth_user)):
    return authUser

@app.post('/user', tags=['User'])
async def create_user(authUser = Depends(userService.auth_user)):
    return authUser

@app.patch('/user/{userID}', tags=['User'])
async def update_user(authUser = Depends(userService.auth_user)):
    return authUser

@app.delete('/user/{userID}', tags=['User'])
async def delete_user(authUser = Depends(userService.auth_user)):
    return authUser
