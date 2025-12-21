import os

from .handlers.logers.loger_handlers import LogerHandler

from .handlers.db.db_handlers import SqliteHandlerAsync
from .handlers.db.orm_models.sqlite_models import (Users,
                                                   AlfaFinancialTransactions,
                                                   TinkoffFinancialTransactions,
                                                   GoalsCatalog,
                                                   FriendsCatalog,
                                                   GoalsRule,
                                                   GoalsOwnersCatalog,
                                                   CastomCategorysCatalog,
                                                   CastomCategorysConditions)

from .handlers.users.user import UserHandler
from .services.users.users import UserService

from .handlers.bank_files.bank_file_preprocessing import (AlfaPreprocessingDataFileHandler,TinkoffPreprocessingDataFileHandler)
from .handlers.bank_files.bank_load_handlers import (AlfaBankHandler, TinkoffBankHandler)
from .handlers.bank_files.bank_registry import BankHandlerRegistry
from .handlers.bank_files.schema import RegistryConstSchema

from .handlers.friends.friends_handler import FriendsCatalogHandler

from .handlers.goals.goals_catalog_handler import GoalsCatalogHandler
from .handlers.goals.goals_owners_handler import GoalOwnersCatalogHandler
from .handlers.goals.goals_rule_handler import GoalsRuleHandler

from .handlers.castom_category.category_catalog_handler import TransactionCategoryCatalogHandler
from .handlers.castom_category.category_conditions_handler import TransactionCategoryConditionsHandler

from .services.load_bank_file_service.load_bank_data import BankService
from .services.friends.friends_service import FriendsService
from .services.goals.goals_service import GoalsService
from .services.category.category import СategoryService



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


goalsCatalogHandler = GoalsCatalogHandler(dbHandler=dbHandler, dbt=GoalsCatalog, logerHandler=logerHandler)
goalOwnersCatalogHandler = GoalOwnersCatalogHandler(dbHandler=dbHandler, dbt=GoalsOwnersCatalog, logerHandler=logerHandler)
goalsRuleHandler = GoalsRuleHandler(dbHandler=dbHandler, dbt=GoalsRule, logerHandler=logerHandler)

friendsCatalogHandler = FriendsCatalogHandler(
    dbHandler=dbHandler, dbt=FriendsCatalog, logerHandler=logerHandler,
    userCatalogHandler=userHandler
)

transactionCategoryHandler = TransactionCategoryCatalogHandler(dbHandler=dbHandler, 
                                                               dbt=CastomCategorysCatalog, 
                                                               logerHandler=logerHandler)
transactionCategoryConditionsHandler = TransactionCategoryConditionsHandler(dbHandler=dbHandler, 
                                                                            dbt=CastomCategorysConditions, 
                                                                            logerHandler=logerHandler)

# Registers (Factory)
bankRegistry = BankHandlerRegistry()

alfaHandlerConfig = RegistryConstSchema(fileStorageDir=os.sep.join(["handlers","bank_files","report_file_catalog","alfa"]))
bankRegistry.register("alfa", alfaBankHandler, alfaHandlerConfig)
tinkoffHandlerConfig = RegistryConstSchema(fileStorageDir=os.sep.join(["handlers","bank_files","report_file_catalog","tinkoff","pdf"]))
bankRegistry.register("tinkoff", tinkoffBankHandler, tinkoffHandlerConfig)

# Services

goalsService = GoalsService(logerHandler=logerHandler,
                            goalsOwnersHandler=goalOwnersCatalogHandler,
                            goalsCatalogHandler=goalsCatalogHandler,
                            goalsRulesHandler=goalsRuleHandler,
                            friendsCatalogHandler=friendsCatalogHandler)

userService = UserService(userHandler=userHandler, logerHandler=logerHandler)

bankService = BankService(logerHandler=logerHandler,bankHandlerRegisry=bankRegistry)

friendsService = FriendsService(logerHandler=logerHandler, friendsCatalogHandler=friendsCatalogHandler)

categoryService = СategoryService(
        categoryCatalogHandler=transactionCategoryHandler,
        categoryConditionsHandler=transactionCategoryConditionsHandler,
        bankRgistry=bankRegistry,
        logerHandler=logerHandler)
