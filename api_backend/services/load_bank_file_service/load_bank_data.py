import os
from typing import Type
from abc import ABC, abstractmethod
from fastapi import File, UploadFile, HTTPException, status

from .schema import CreateServiceBankTransactions, SearchParametrs
from ..users.schama import AuthUser
from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.bank_files.schema import TinkoffHandlerUpdateData,AlfaHandlerUpdateData
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
    def update_bank_transactions(self):
        pass

    @abstractmethod
    def delete_bank_transactions(self):
        pass

class BankService(AbstractBankService):
    def __init__(self, logerHandler, bankHandlerRegisry):
        super().__init__(logerHandler)
        self.bankHandlerRegisry:BankHandlerRegistry = bankHandlerRegisry

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
    
    async def create_bank_transactions(self, authUser:AuthUser,slug:str, dto:CreateServiceBankTransactions):
        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        # dto.operationDate = datetime.strptime(dto.operationDate,"%Y-%m-%d")
        insertingData = await bankHandler.insert_data(operationDate = dto.operationDate,
                                                      currencyAmount = dto.currencyAmount,
                                                      description = dto.description,
                                                      userID=authUser.get("id"), fileName="manual load")
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

    async def update_bank_transactions(self,authUser:AuthUser, transactionID:int, slug:str, updateData:TinkoffHandlerUpdateData|AlfaHandlerUpdateData):
        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        getTrans = await bankHandler.get_data((bankHandler.dbt.id == transactionID,))
        
        if not (getTrans[0].to_dict().get('userID') == authUser.get('id')):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        
        updatedData = await bankHandler.update_data(transactionID, updateData)
        return updatedData

    async def delete_bank_transactions(self, authUser:AuthUser, slug:str, deleteFiletr:SearchParametrs):
        bankHandler = self.bankHandlerRegisry.get_handler(slug)
        deletefilter = self._get_sarch_filetr(authUser, bankHandler, deleteFiletr)
        deleteData = await bankHandler.delete_data(deletefilter)
        return deleteData
    
