from abc import ABC, abstractmethod

from ..bank_files.bank_registry import BankHandlerRegistry
from ..logers.loger_handlers import LogerHandler
from ..friends.friends_handler import AbstractFriendsCatalogHandler
from ..goals.goals_catalog_handler import AbstractGoalsCatalogHandler
from ..goals.goals_owners_handler import AbstractGoalOwnersCatalogHandler
from ..goals.goals_rule_handler import AbstractGoalsRuleHandler

class AbstractAnalyticsHandler(ABC):
    @abstractmethod
    def __init__(self,logerHnadler, bankFactory, goalCatalogHandler, goalOwnersHandler, goalOperatorsHandler, friendsHandler):
        super().__init__()
        self.logerHnadler:LogerHandler = logerHnadler
        self.bankFactory:BankHandlerRegistry = bankFactory
        self.goalCatalogHandler:AbstractGoalsCatalogHandler = goalCatalogHandler
        self.goalOwnersHandler:AbstractGoalOwnersCatalogHandler = goalOwnersHandler
        self.goalOperatorsHandler:AbstractGoalsRuleHandler = goalOperatorsHandler
        self.friendsHandler:AbstractFriendsCatalogHandler = friendsHandler
    
    @abstractmethod
    def get_balance(self):
        pass

    @abstractmethod
    def get_last_transactions(self, limit:int):
        pass

    @abstractmethod
    def get_last_bank_transactions(self, limit:int):
        pass