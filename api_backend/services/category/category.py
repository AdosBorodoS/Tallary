from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from datetime import date, datetime
from abc import ABC, abstractmethod
from fastapi import HTTPException, status
from typing import List, Dict, Any, Optional

from .schema import *
from ...handlers.castom_category.schema import *
from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.bank_files.bank_registry import BankHandlerRegistry
from ...handlers.castom_category.category_catalog_handler import AbstractTransactionCategoryHandler
from ...handlers.castom_category.category_conditions_handler import AbstractTransactionCategoryConditionsHandler
from ...handlers.bank_files.bank_slugs import BankSlugs

class AbstractСategoryService(ABC):
    @abstractmethod
    def __init__(self, categoryCatalogHandler, categoryConditionsHandler, bankRgistry, logerHandler, bankSlugsCatalog):
        super().__init__()
        self.logerHandler: LogerHandler = logerHandler
        self.bankRgistry: BankHandlerRegistry = bankRgistry
        self.bankSlugsCatalog: BankSlugs = bankSlugsCatalog
        self.categoryCatalogHandler: AbstractTransactionCategoryHandler = categoryCatalogHandler
        self.categoryConditionsHandler: AbstractTransactionCategoryConditionsHandler = categoryConditionsHandler

    @abstractmethod
    def get_transactions(self, slugs:str, userID:int):
        pass

    @abstractmethod
    def get_categorys(self, userID: int):
        pass

    @abstractmethod
    def add_category(self, userID:int, addData: AddCategoryServiceSchema):
        pass

    @abstractmethod
    def delete_category(self, userID: int, categoryID: int):
        pass

    @abstractmethod
    def update_category(self, userID: int, categoryID: int, updateData: UpdateDataServiceSchema):
        pass

class СategoryService(AbstractСategoryService):
    def __init__(self, categoryCatalogHandler, categoryConditionsHandler, bankRgistry, logerHandler,bankSlugsCatalog):
        super().__init__(categoryCatalogHandler, categoryConditionsHandler, bankRgistry, logerHandler,bankSlugsCatalog)

    async def _is_category_exists(self, userID: int, categoryID: int):
        # Проверка на наличее категории у пользователя
        categoryItem = await self.categoryCatalogHandler.get_category((
            self.categoryCatalogHandler.dbt.id == categoryID,
            self.categoryCatalogHandler.dbt.userID == userID,))

        if categoryItem.__len__() == 0:
            return False
        return True

    async def __error_if_category_not_found(self, userID: int, categoryID: int):
        if not await self._is_category_exists(userID, categoryID):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Category with ID {categoryID} not found for user {userID}.")

    def _to_iso_date(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (date, datetime)):
            return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
        if isinstance(value, str):
            return value
        return str(value)

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_text(self, text: Any) -> str:
        return ("" if text is None else str(text)).strip()

    def _normalize_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        idValue = self._to_int(transaction.get("id"))
        userIDValue = self._to_int(transaction.get("userID"))
        fileNameValue = transaction.get("fileName")

        operationDateValue = self._to_iso_date(transaction.get("operationDate"))
        postingDateValue = self._to_iso_date(transaction.get("postingDate"))

        codeValue = transaction.get("code")
        bankCategoryValue = transaction.get("category")
        descriptionValue = transaction.get("description")
        description2Value = transaction.get("description2")

        currencyAmountValue = self._to_float(transaction.get("currencyAmount"))
        amountValue = self._to_float(transaction.get("amount"))
        slugValue = transaction.get("slug")
        statusValue = transaction.get("status")

        return {
            "id": idValue,
            "userID": userIDValue,
            "fileName": fileNameValue,
            "operationDate": operationDateValue,
            "postingDate": postingDateValue,
            "code": codeValue,
            "slug": slugValue,
            "bankCategory": bankCategoryValue,     # исходная категория банка/БД (может быть None)
            "customCategory": None,               # сюда проставим кастомную категорию (если совпадет правило)
            "category": bankCategoryValue,       # итоговая категория (кастомная имеет приоритет)

            "description": descriptionValue,
            "description2": description2Value,
            "currencyAmount": currencyAmountValue,
            "amount": amountValue,
            "status": statusValue,
        }

    def _is_condition_match(self, haystack: str, conditionValue: str, isExact: bool) -> bool:
        haystackNormalized = self._normalize_text(haystack)
        needle = self._normalize_text(conditionValue)

        if not needle:
            return False

        if isExact:
            return haystackNormalized == needle

        return needle in haystackNormalized

    def _resolve_custom_category_name(
        self,
        normalizedTransaction: Dict[str, Any],
        categorys: List[Dict[str, Any]],
        matchFields: List[str],
    ) -> Optional[str]:
        
        matchValues = [self._normalize_text(normalizedTransaction.get(fieldName)) for fieldName in matchFields]
        joinedHaystack = " | ".join([v for v in matchValues if v])

        for categoryItem in categorys:
            categoryName = self._normalize_text(categoryItem.get("categoryName"))
            conditions = categoryItem.get("categoryConditions") or []

            for condition in conditions:
                conditionValue = self._normalize_text(condition.get("conditionValue"))
                isExact = bool(condition.get("isExact", False))

                if isExact:
                    for fieldValue in matchValues:
                        if self._is_condition_match(fieldValue, conditionValue, True):
                            return categoryName
                else:
                    if self._is_condition_match(joinedHaystack, conditionValue, False):
                        return categoryName

        return None

    def group_by_category(
        self,
        categorys: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
        matchFields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if matchFields is None:
            matchFields = ["description", "description2", "code"]

        processed: List[Dict[str, Any]] = []
        matchedCount = 0

        for transaction in transactions:
            normalizedTx = self._normalize_transaction(transaction)

            customCategoryName = self._resolve_custom_category_name(
                normalizedTransaction=normalizedTx,
                categorys=categorys,
                matchFields=matchFields,
            )

            if customCategoryName:
                normalizedTx["customCategory"] = customCategoryName
                normalizedTx["category"] = customCategoryName
                matchedCount += 1
            else:
                if normalizedTx["category"] is None:
                    normalizedTx["category"] = "Прочие операции"

            processed.append(normalizedTx)

        return {
            "status": "success",
            "data": processed,
            "meta": {
                "total": len(processed),
                "matchedCustom": matchedCount,
                "unmatchedCustom": len(processed) - matchedCount,
                "matchFields": matchFields,
            },
        }

    async def get_transactions(self, slugs: str, userID: int):
        transactionsPull = []

        for slug in slugs.split(","):
            slugValue = slug.strip()
            if not slugValue:
                continue

            bankHandler = self.bankRgistry.get_handler(slugValue)
            getBankTransactionFilter = (bankHandler.dbt.userID == userID,)
            bankData = await bankHandler.get_data(getBankTransactionFilter)

            # Важно: ставим slug на транзакции конкретного банка до merge в общий пул
            for item in bankData:
                transactionDict = item.to_dict()
                transactionDict["slug"] = slugValue
                transactionsPull.append(transactionDict)

        categoryCatalog = await self.get_categorys(userID)

        result = self.group_by_category(
            categorys=categoryCatalog,
            transactions=transactionsPull,
            matchFields=["description", "description2", "code"],
        )

        return result

    async def _get_all_transactions_pull(self, userID: int) -> List[Dict[str, Any]]:
        transactionsPull: List[Dict[str, Any]] = []

        for slugValue in self.bankSlugsCatalog.all():
            bankHandler = self.bankRgistry.get_handler(slugValue)
            bankData = await bankHandler.get_data((bankHandler.dbt.userID == userID,))
            transactionsPull.extend([x.to_dict() for x in bankData])

        return transactionsPull

    def _calc_category_stats(
        self,
        categorys: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
        matchFields: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        if matchFields is None:
            matchFields = ["description", "description2", "code"]

        stats: Dict[str, Dict[str, Any]] = {}

        for tx in transactions:
            normalizedTx = self._normalize_transaction(tx)

            customCategoryName = self._resolve_custom_category_name(
                normalizedTransaction=normalizedTx,
                categorys=categorys,
                matchFields=matchFields,
            )

            if customCategoryName:
                finalCategory = customCategoryName
            else:
                finalCategory = normalizedTx.get("bankCategory") or "Прочие операции"

            amountValue = normalizedTx.get("currencyAmount")
            if amountValue is None:
                amountValue = 0.0

            if finalCategory not in stats:
                stats[finalCategory] = {"transactionsCount": 0, "amountSum": 0.0}

            stats[finalCategory]["transactionsCount"] += 1
            stats[finalCategory]["amountSum"] += float(amountValue or 0.0)

        return stats

    async def get_categorys(self, userID: int):
        getCategoryCatalogFilter = (self.categoryCatalogHandler.dbt.userID == userID,)
        userCategoryCatalog = await self.categoryCatalogHandler.get_category(getCategoryCatalogFilter)

        categoryData = []
        for categoryID in userCategoryCatalog:
            getCategoryConditionFilter = (self.categoryConditionsHandler.dbt.categoryID == categoryID.id,)
            categoryConditionsCatalog = await self.categoryConditionsHandler.get_category_conditions(getCategoryConditionFilter)

            categoryData.append({
                "id": categoryID.id,
                "categoryName": categoryID.categoryName,
                "categoryConditions": [x.to_dict() for x in categoryConditionsCatalog]
            })

        transactionsPull = await self._get_all_transactions_pull(userID=userID)
        statsMap = self._calc_category_stats(
            categorys=categoryData,
            transactions=transactionsPull,
            matchFields=["description", "description2", "code"],
        )

        for c in categoryData:
            name = self._normalize_text(c.get("categoryName"))
            s = statsMap.get(name, {"transactionsCount": 0, "amountSum": 0.0})
            c["transactionsCount"] = int(s["transactionsCount"])
            c["amountSum"] = float(s["amountSum"])

        return categoryData

    async def add_category(self, userID:int, addData: AddCategoryServiceSchema):
        newCategory = await self.categoryCatalogHandler.add_category(AddCategoryCatalogSchema(userID=userID, categoryName=addData.categoryName))
        newCategory = newCategory[0]
        newCategory.update({"conditionsValues": []})

        for categoryConditions in addData.conditionValues:
            newCategoryConditions = await self.categoryConditionsHandler.add_category_conditions(AddCategoryConditionsSchema(
                categoryID=newCategory.get("id"), 
                conditionValue=categoryConditions.conditionValue, 
                isExact=categoryConditions.isExact,))

            newCategory.get("conditionsValues").append(newCategoryConditions[0])

        return newCategory
        
    async def delete_category(self, userID: int, categoryID: int):
        # Это что бизнес логика? лол
        await self.__error_if_category_not_found(userID, categoryID)

        # удаление из каталога
        deleteCategory = await self.categoryCatalogHandler.delete_category(categoryID)
        
        getDeletCategoryConditionsIdFilter = (self.categoryConditionsHandler.dbt.categoryID == categoryID,)
        conditionsIDCatalog = await self.categoryConditionsHandler.get_category_conditions(getDeletCategoryConditionsIdFilter)
        
        # удаление из условий
        conditionsData = []
        for condition in conditionsIDCatalog:
            print(condition.id)
            deletedConditions = await self.categoryConditionsHandler.delete_category_conditions(condition.id)
            conditionsData.append({"id":condition.id,"status":deletedConditions})

        return {"deleteCategoryID":categoryID, "deleteCategoryStatus":deleteCategory, "deleteCategoryCondtitions":conditionsData}

    async def update_category(self, userID: int, categoryID: int, updateData: UpdateDataServiceSchema):
        await self.__error_if_category_not_found(userID, categoryID)

        if updateData.categoryName is not None:
            updatedCategory = await self.categoryCatalogHandler.update_category(UpdateDataCatalogSchema(
                categoryID=categoryID,
                categoryName=updateData.categoryName))

        conditionUpdateData = []
        if updateData.conditionValues:
            for condition in updateData.conditionValues:
                updatedConditions = await self.categoryConditionsHandler.update_category_conditions(UpdateDataConditionsSchema(
                    conditionID=condition.conditionID,
                    conditionValue=condition.conditionValue,
                    isExact=condition.isExact,
                ))
                conditionUpdateData.append(updatedConditions)

        return {"updatedCategoryID":categoryID, "updatedCategoryCondtitions":conditionUpdateData}

    async def add_category_condition(self, userID: int, addContitionData:AddCategoryConditionsSchema):
        await self.__error_if_category_not_found(userID, addContitionData.categoryID)

        newCategoryConditions = await self.categoryConditionsHandler.add_category_conditions(AddCategoryConditionsSchema(
            categoryID=addContitionData.categoryID, 
            conditionValue=addContitionData.conditionValue, 
            isExact=addContitionData.isExact,))
        
        return newCategoryConditions
    
    async def delete_category_condition(self, userID: int, categoryID:int, deleteContitionData:DeleteCategoryConditionsSchema):
        await self.__error_if_category_not_found(userID, categoryID)

        async with self.categoryConditionsHandler.dbHandler.Session() as sess:
            stmt = sa_delete(self.categoryConditionsHandler.dbt)
            stmt = stmt.where(self.categoryConditionsHandler.dbt.id == deleteContitionData.conditionID)
            result = await sess.execute(stmt)
            await sess.commit()
            return {"status": result.rowcount or 0}
