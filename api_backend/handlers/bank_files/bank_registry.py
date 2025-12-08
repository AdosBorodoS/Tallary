from typing import Dict, Type
from .bank_load_handlers import AbstractBankFileHandler

class BankHandlerRegistry:
    def __init__(self):
        self._handlers: Dict[str, AbstractBankFileHandler] = {}

    def register(self, bankSlug: str, handlerObj: Type[AbstractBankFileHandler]):
        self._handlers[bankSlug] = handlerObj

    def get_handler(self, bankSlug: str) -> AbstractBankFileHandler:
        if bankSlug not in self._handlers:
            raise ValueError(f"Handler for bank '{bankSlug}' not registered")
        return self._handlers[bankSlug]