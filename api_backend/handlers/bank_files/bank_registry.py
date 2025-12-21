from fastapi import HTTPException, status
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

    def _is_slug_exist(self, slug:str):
        if slug in self._handlers:
            return True
        return False
    
    def _error_ifslug_does_not_registered(self, slug:str):
        if not self._is_slug_exist(slug):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Slug: {slug} does not registered")

    def get_handler(self, bankSlug: str) -> AbstractBankFileHandler:
        self._error_ifslug_does_not_registered(bankSlug)
        return self._handlers[bankSlug]
    
    def get_const(self, bankSlug: str) -> RegistryConstSchema:
        self._error_ifslug_does_not_registered(bankSlug)
        return self._handlers_const[bankSlug]