import os

from .handlers.logers.loger_handlers import LogerHandler

from .handlers.db.db_handlers import SqliteHandlerAsync
from .handlers.db.orm_models.sqlite_models import (Users,AlfaFinancialTransactions,TinkoffFinancialTransactions)

from .handlers.users.user import UserHandler
from .services.users.users import UserService

from .handlers.bank_files.bank_file_preprocessing import (AlfaPreprocessingDataFileHandler,TinkoffPreprocessingDataFileHandler)
from .handlers.bank_files.bank_load_handlers import (AlfaBankHandler, TinkoffBankHandler)
from .handlers.bank_files.bank_registry import BankHandlerRegistry
from .handlers.bank_files.schema import RegistryConstSchema

from .services.load_bank_file_service.load_bank_data import BankService

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

# Registers (Factory)
bankRegistry = BankHandlerRegistry()

alfaHandlerConfig = RegistryConstSchema(fileStorageDir=os.sep.join(["handlers","bank_files","report_file_catalog","alfa"]))
bankRegistry.register("alfa", alfaBankHandler, alfaHandlerConfig)
tinkoffHandlerConfig = RegistryConstSchema(fileStorageDir=os.sep.join(["handlers","bank_files","report_file_catalog","tinkoff","pdf"]))
bankRegistry.register("tinkoff", tinkoffBankHandler, tinkoffHandlerConfig)

# print('>>>>>>>>>>>>------------------------')
# print(bankRegistry.get_const('alfa').to_dict())
# print('>>>>>>>>>>>>------------------------')

# Services

userService = UserService(userHandler=userHandler, logerHandler=logerHandler)



bankService = BankService(logerHandler=logerHandler,bankHandlerRegisry=bankRegistry)



