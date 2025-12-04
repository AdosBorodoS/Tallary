from .handlers.db.db_handlers import SqliteHandlerAsync
from .handlers.db.orm_models.sqlite_models import Users
from .handlers.users.user import UserHandler
from .handlers.logers.loger_handlers import LogerHandler
from .services.users.users import UserService


logerHandler = None

dbHandler = SqliteHandlerAsync(url="sqlite+aiosqlite:///database/database_draft.db")
userHandler = UserHandler(dbHandler=dbHandler, dbt=Users, logerHandler=logerHandler)

userService = UserService(userHandler=userHandler,logerHandler=logerHandler)


