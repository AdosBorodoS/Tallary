import os
from typing import Type, Any
from abc import ABC, abstractmethod
from fastapi import File, UploadFile, HTTPException, status
from collections import Counter

from .schema import CreateServiceBankTransactions, SearchParametrs
from ..users.schama import AuthUser
from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.bank_files.schema import TinkoffHandlerUpdateData,AlfaHandlerUpdateData, CreateHandlerBankTransactions, CashHandlerUpdateData,DeleteTransactionSchema
from ...handlers.bank_files.bank_registry import BankHandlerRegistry
from ...handlers.bank_files.bank_load_handlers import AbstractBankFileHandler



class AbstractBankService(ABC):
    @abstractmethod
    def __init__(self, logerHandler):
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
    def get_loaded_files_catalog(self, authUser:AuthUser, slugs:str):
        pass

    @abstractmethod
    def update_bank_transactions(self):
        pass

    @abstractmethod
    def delete_bank_transactions(self):
        pass

class BankService(AbstractBankService):
    def __init__(self, logerHandler, bankHandlerRegisry):
        super().__init__(logerHandler)
        self.bankHandlerRegisry:BankHandlerRegistry = bankHandlerRegisry


    async def _is_transaction_exist(self,bankHandler:AbstractBankFileHandler,transactionID:int):
        getTrans = await bankHandler.get_data((bankHandler.dbt.id == transactionID,))
        if getTrans.__len__():
            return True
        return False
    
    async def _is_user_transaction_exist(self,bankHandler:AbstractBankFileHandler, transactionID:int, userID):
        getTrans = await bankHandler.get_data((bankHandler.dbt.id == transactionID,))
        if (getTrans[0].to_dict().get('userID') == userID):
            return True
        return False

    async def _raise_transaction(self, userID:int, bankHandler:AbstractBankFileHandler, transactionID:int):
        if not await self._is_transaction_exist(bankHandler=bankHandler, transactionID=transactionID):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

        if not await self._is_user_transaction_exist(bankHandler=bankHandler,transactionID=transactionID, userID=userID):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User transaction not found") 

    def _get_sarch_filetr(self, authUser:AuthUser, bankHandler:Type[AbstractBankFileHandler], getFiletr:SearchParametrs):
        
        filterPull=[]
        filterPull.append(bankHandler.dbt.userID == authUser.get('id'))
        for k,v in getFiletr.to_dict().items():
            if v is None:
                continue
            match k:
                case "eq_operationDate":
                    filterPull.append(bankHandler.dbt.operationDate == v)
                
                case "ge_operationDate":
                    filterPull.append(bankHandler.dbt.operationDate >= v)
                
                case "le_operationDate":
                    filterPull.append(bankHandler.dbt.operationDate <= v)
                
                case "like_description":
                    filterPull.append(bankHandler.dbt.description.like(f'%{v}%'))
                
                case "ge_currencyAmount":
                    filterPull.append(bankHandler.dbt.currencyAmount >= v)
                
                case "le_currencyAmount":
                    filterPull.append(bankHandler.dbt.currencyAmount <= v)
                
                case _:
                    pass

        return filterPull
 
    async def get_bank_transactions(self, authUser:AuthUser, slug:str, getFiletr:SearchParametrs):
        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        getfilter = self._get_sarch_filetr(authUser, bankHandler, getFiletr)
        gotData = await bankHandler.get_data(getfilter)
        return gotData
    
    async def create_bank_transactions(self, authUser:AuthUser, slug:str, addData:CreateServiceBankTransactions):
        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        addTransactionData = CreateHandlerBankTransactions(userID=authUser.get('id'),
                                      fileName='Manual load',
                                      currencyAmount=addData.currencyAmount,
                                      description=addData.description,
                                      operationDate=addData.operationDate)
        insertingData = await bankHandler.insert_data(addTransactionData)
        return {"loaded rows":insertingData.__len__()}

    async def save_uploaded_file(self, file: UploadFile, slug:str) -> str:
        # Write file
        safeFilename, fileExtension = os.path.splitext(file.filename)  # .pdf, .xlsx ...
        # safeFilename = f"{uuid.uuid4().hex}{fileExtension}"
        handlerConstantConfig = self.bankHandlerRegisry.get_const(slug).fileStorageDir
        filePath = os.path.join(handlerConstantConfig, safeFilename)

        with open(filePath, "wb") as f:
            content = await file.read()
            f.write(content)

        return handlerConstantConfig, safeFilename

    async def create_bank_transactions_by_load_file(self, authUser:AuthUser, slug:str, file: UploadFile) -> dict:
        handlerConstantConfig, safeFilename = await self.save_uploaded_file(file,slug)

        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        filePath = os.sep.join([handlerConstantConfig,safeFilename])
        insertedFileResponse = await bankHandler.insert_file(filePath=filePath, userID=authUser.get("id"))
        os.remove(filePath)
        return {"file":safeFilename,"loaded rows":insertedFileResponse.__len__()}

    async def update_bank_transactions(self, authUser:AuthUser, transactionID:int, slug:str, updateData:TinkoffHandlerUpdateData|AlfaHandlerUpdateData|CashHandlerUpdateData):
        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        await self._raise_transaction(bankHandler=bankHandler, userID=authUser.get('id'), transactionID=transactionID)

        updatedData = await bankHandler.update_data(transactionID, updateData)
        return updatedData

    async def delete_bank_transactions(self, authUser:AuthUser, slug:str, transactionID:int):
        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        await self._raise_transaction(bankHandler=bankHandler, userID=authUser.get('id'), transactionID=transactionID)
        
        deleteData = await bankHandler.delete_data(DeleteTransactionSchema(transactionID=transactionID))
        return {"msg":"Transaction deleted successfully","status":deleteData}

    @staticmethod
    def _build_files_stats_response(rowsList: list[Any]) -> dict:
        counter = {}

        for transaction in rowsList:
            if transaction.fileName not in counter and not (transaction.fileName is None):
               counter.update({transaction.fileName:1})
            if transaction.fileName in counter and not (transaction.fileName is None): 
               counter[transaction.fileName] += 1

        return counter

    async def get_loaded_files_catalog(self, authUser:AuthUser, slugs:str):
        
        filesPull = []
        for slug in slugs.split(","): 
            bankHandler = self.bankHandlerRegisry.get_handler(slug)
            
            getfilter = (bankHandler.dbt.userID == authUser.get('id'),)
            gotData = await bankHandler.get_data(getfilter)
            filesPull.append(self._build_files_stats_response(gotData))

        loadedFiles = [{"fileName":k, "rows":y} for x in filesPull for k,y in x.items()]

        return {"status":True, "data":loadedFiles}
