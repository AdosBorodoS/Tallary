from abc import ABC, abstractmethod

from ...handlers.logers.loger_handlers import LogerHandler
from ..users.schama import AuthUser
from ...handlers.bank_files.shcema import TinkoffUpdateData,AlfaUpdateData

class AbstractBankService(ABC):
    @abstractmethod
    def __init__(self, logerHandler, userHandler):
        super().__init__()
        self.logerHandler:LogerHandler = logerHandler

    @abstractmethod
    def get_bank_transactions(self):
        pass
    
    @abstractmethod
    def create_bank_transactions(self):
        pass

    @abstractmethod
    def create_bank_transactions_by_load_file(self):
        pass

    @abstractmethod
    def update_bank_transactions(self):
        pass

    @abstractmethod
    def delete_bank_transactions(self):
        pass

class BankService(AbstractBankService):
    def __init__(self, logerHandler, userHandler):
        super().__init__(logerHandler, userHandler)

    def get_bank_transactions(self, authUser:AuthUser):
        pass
    
    def create_bank_transactions(self, authUser:AuthUser):
        pass

    def create_bank_transactions_by_load_file(self, authUser:AuthUser):
        pass

    def update_bank_transactions(self, authUser:AuthUser, updateData:TinkoffUpdateData|AlfaUpdateData):
        pass

    def delete_bank_transactions(self, authUser:AuthUser, deleteFilter:tuple):
        pass
    
