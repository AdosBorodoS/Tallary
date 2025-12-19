from abc import ABC, abstractmethod

class AbstractTransactionCategoryHandler(ABC):

    @abstractmethod
    def __init__(self, dbt, logerHandler, dbHandler):
        super().__init__()
        self.dbt = dbt
        self.logerHandler = logerHandler
        self.dbHandler = dbHandler

    @abstractmethod
    def add_category(self):
        pass

    @abstractmethod
    def delete_category(self):
        pass

    @abstractmethod
    def update_category(self,):
        pass

    @abstractmethod
    def get_category(self, columnType:List):
        pass
