import os

from .handlers.logers.loger_handlers import LogerHandler

from .handlers.db.db_handlers import SqliteHandlerAsync
from .handlers.db.orm_models.sqlite_models import (Users,AlfaFinancialTransactions,TinkoffFinancialTransactions,GoalsCatalog, FriendsCatalog)

from .handlers.users.user import UserHandler
from .services.users.users import UserService

from .handlers.bank_files.bank_file_preprocessing import (AlfaPreprocessingDataFileHandler,TinkoffPreprocessingDataFileHandler)
from .handlers.bank_files.bank_load_handlers import (AlfaBankHandler, TinkoffBankHandler)
from .handlers.bank_files.bank_registry import BankHandlerRegistry
from .handlers.bank_files.schema import RegistryConstSchema

from .handlers.goals.goals_catalog import GoalsCatalogHandler
from .handlers.friends.friends_handler import FriendsCatalogHandler


from .services.load_bank_file_service.load_bank_data import BankService
from .services.friends.friends_service import FriendsService



# Handlers

logerHandler = None

dbHandler = SqliteHandlerAsync(url="sqlite+aiosqlite:///database/database_draft.db")

userHandler = UserHandler(dbHandler=dbHandler, dbt=Users, logerHandler=logerHandler)

alfaPreprocessingDataFileHandler = AlfaPreprocessingDataFileHandler(logerHandler=logerHandler,)

tinkoffPreprocessingDataFileHandler = TinkoffPreprocessingDataFileHandler(logerHandler=logerHandler,)

alfaBankHandler = AlfaBankHandler(dbHandler=dbHandler,
                                  dbt=AlfaFinancialTransactions,
                                  logerHandler=logerHandler,
                                  preprocessingHandler=alfaPreprocessingDataFileHandler)

tinkoffBankHandler = TinkoffBankHandler(dbHandler=dbHandler,
                                        dbt=TinkoffFinancialTransactions,
                                        logerHandler=logerHandler,
                                        preprocessingHandler=tinkoffPreprocessingDataFileHandler)


goalsCAtalogHandler = GoalsCatalogHandler(dbHandler=dbHandler, dbt=GoalsCatalog, logerHandler=logerHandler)

friendsCatalogHandler = FriendsCatalogHandler(
    dbHandler=dbHandler, dbt=FriendsCatalog, logerHandler=logerHandler,
    userCatalogHandler=userHandler
)

# Registers (Factory)
bankRegistry = BankHandlerRegistry()

alfaHandlerConfig = RegistryConstSchema(fileStorageDir=os.sep.join(["handlers","bank_files","report_file_catalog","alfa"]))
bankRegistry.register("alfa", alfaBankHandler, alfaHandlerConfig)
tinkoffHandlerConfig = RegistryConstSchema(fileStorageDir=os.sep.join(["handlers","bank_files","report_file_catalog","tinkoff","pdf"]))
bankRegistry.register("tinkoff", tinkoffBankHandler, tinkoffHandlerConfig)

# Services

userService = UserService(userHandler=userHandler, logerHandler=logerHandler)
bankService = BankService(logerHandler=logerHandler,bankHandlerRegisry=bankRegistry)
friendsService = FriendsService(logerHandler=logerHandler, friendsCatalogHandler=friendsCatalogHandler)


