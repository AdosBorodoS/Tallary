from typing import List
from abc import ABC, abstractmethod
from fastapi import HTTPException, status

from .schema import *
from ...handlers.castom_category.schema import *
from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.bank_files.bank_registry import BankHandlerRegistry
from ...handlers.castom_category.category_catalog_handler import AbstractTransactionCategoryHandler
from ...handlers.castom_category.category_conditions_handler import AbstractTransactionCategoryConditionsHandler


class AbstractСategoryService(ABC):
    @abstractmethod
    def __init__(self, categoryCatalogHandler, categoryConditionsHandler, bankRgistry, logerHandler):
        super().__init__()
        self.logerHandler: LogerHandler = logerHandler
        self.bankRgistry: BankHandlerRegistry = bankRgistry
        self.categoryCatalogHandler: AbstractTransactionCategoryHandler = categoryCatalogHandler
        self.categoryConditionsHandler: AbstractTransactionCategoryConditionsHandler = categoryConditionsHandler

    @abstractmethod
    def get_transactions(self, slug: List, filterBy: List):
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
    def __init__(self, categoryCatalogHandler, categoryConditionsHandler, bankRgistry, logerHandler):
        super().__init__(categoryCatalogHandler, categoryConditionsHandler, bankRgistry, logerHandler)

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

    async def get_transactions(self, slug: List, filterBy: List):
        pass

    async def get_categorys(self, userID: int):
        getCategoryCatalogFilter = (self.categoryCatalogHandler.dbt.userID == userID,)
        userCategoryCatalog = await self.categoryCatalogHandler.get_category(getCategoryCatalogFilter)

        categoryData = []
        for categoryID in userCategoryCatalog:
            getCategoryConditionFilter = (self.categoryConditionsHandler.dbt.categoryID == categoryID.id,)
            categoryConditionsCatalog = await self.categoryConditionsHandler.get_category_conditions(getCategoryConditionFilter)

            categoryData.append({
                "id":categoryID.id,
                "categoryName":categoryID.categoryName,
                "categoryConditions":categoryConditionsCatalog
            })
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

