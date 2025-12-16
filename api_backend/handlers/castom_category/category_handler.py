from abc import ABC, abstractmethod

from ..bank_files.bank_registry import BankHandlerRegistry

class AbstractTransactionCategoryHandler(ABC):

    @abstractmethod
    def __init__(self,bankFactory):
        super().__init__()
        self.bankFactory:BankHandlerRegistry = bankFactory
            


