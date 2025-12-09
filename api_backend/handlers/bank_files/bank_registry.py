from typing import Dict, Type
from .bank_load_handlers import AbstractBankFileHandler
from .schema import RegistryConstSchema
class BankHandlerRegistry:
    def __init__(self):
        self._handlers: Dict[str, AbstractBankFileHandler] = {}
        self._handlers_const: Dict[str,RegistryConstSchema] = {}
        self.slugNameList:list = []

    def register(self, bankSlug: str, handlerObj: Type[AbstractBankFileHandler], const:RegistryConstSchema | Dict = {}):
        self._handlers[bankSlug] = handlerObj
        self._handlers_const[bankSlug] = const
        self.slugNameList.append(bankSlug)

    def get_handler(self, bankSlug: str) -> AbstractBankFileHandler:
        if bankSlug not in self._handlers:
            raise ValueError(f"Handler for bank '{bankSlug}' not registered")
        return self._handlers[bankSlug]
    
    def get_const(self, bankSlug: str) -> RegistryConstSchema:
        if bankSlug not in self._handlers:
            raise ValueError(f"Constant config for bank '{bankSlug}' not registered")
        return self._handlers_const[bankSlug]