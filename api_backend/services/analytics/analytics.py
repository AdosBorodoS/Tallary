from abc import ABC, abstractmethod
from typing import Any, Dict, List
from collections import defaultdict
from datetime import date, datetime
from fastapi import HTTPException, status

from ..category.category import AbstractСategoryService
from ...handlers.bank_files.bank_slugs import BankSlugs
from ...handlers.bank_files.bank_registry import BankHandlerRegistry
from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.friends.friends_handler import AbstractFriendsCatalogHandler
from ...handlers.goals.goals_catalog_handler import AbstractGoalsCatalogHandler
from ...handlers.goals.goals_owners_handler import AbstractGoalOwnersCatalogHandler
from ...handlers.goals.goals_rule_handler import AbstractGoalsRuleHandler


class AbstractAnalyticsService(ABC):

    @abstractmethod
    def __init__(self,logerHandler,bankSlugsCatalog,bankFactory,goalCatalogHandler,goalOwnersHandler,goalRuleHandler,friendsHandler,categoryService,):
        super().__init__()
        self.bankSlugsCatalog: BankSlugs = bankSlugsCatalog
        self.logerHandler: LogerHandler = logerHandler
        self.bankFactory: BankHandlerRegistry = bankFactory
        self.goalCatalogHandler: AbstractGoalsCatalogHandler = goalCatalogHandler
        self.goalOwnersHandler: AbstractGoalOwnersCatalogHandler = goalOwnersHandler
        self.goalRuleHandler: AbstractGoalsRuleHandler = goalRuleHandler
        self.friendsHandler: AbstractFriendsCatalogHandler = friendsHandler
        self.categoryService: AbstractСategoryService = categoryService

    # БАЗОВАЯ АНАЛИТИКА
    @abstractmethod
    def get_balance(self, userID: int) -> Dict[str, float]:
        # Текущий баланс пользователя.
        pass

    @abstractmethod
    def get_cash_flow(self, userID: int, period: str) -> List[Dict[str, Any]]:
        # Денежный поток (доходы / расходы) по периодам.
        # period: day | month | year
        pass

    @abstractmethod
    def get_expense_category_distribution(self, userID: int) -> Dict[str, Any]:
        # Donut / Pie структура расходов по категориям.
        pass

    @abstractmethod
    def get_income_category_distribution(self, userID: int) -> Dict[str, Any]:
        # Donut / Pie структура доходов по категориям.
        pass

    @abstractmethod
    def get_last_transactions(self, userID: int, limit: int = 10) -> List[Dict[str, Any]]:
        # Последние пользовательские операции.
        pass

    @abstractmethod
    def get_last_bank_transactions(self, userID: int, limit: int = 10) -> List[Dict[str, Any]]:
        # Последние операции, загруженные из банковских файлов.
        pass

    # «УМНАЯ» АНАЛИТИКА (MVP)
    @abstractmethod
    def get_anomaly_transactions(self, userID: int) -> List[Dict[str, Any]]:
        # Нетипичные (аномальные) траты пользователя.
        pass

    @abstractmethod
    def get_habits_cost(self, userID: int) -> List[Dict[str, Any]]:
        # Стоимость финансовых привычек (месяц / год).
        pass

    @abstractmethod
    def get_user_financial_profile(self, userID: int) -> Dict[str, Any]:
        # Финансовый профиль пользователя (описательная аналитика).
        pass

    # СКОРИНГ
    @abstractmethod
    def get_financial_health_score(self, userID: int) -> Dict[str, Any]:
        #Индекс финансового здоровья (0–100).
        pass

    # ПРОГНОЗИРОВАНИЕ (PREDICTION)
    @abstractmethod
    def predict_next_month_expenses(self, userID: int) -> Dict[str, Any]:
        # Прогноз общих расходов на следующий месяц.
        pass

    @abstractmethod
    def predict_category_expenses(self, userID: int) -> List[Dict[str, Any]]:
        # Прогноз расходов по категориям.
        pass

class AnalyticsService(AbstractAnalyticsService):
    def __init__(self, logerHandler, bankSlugsCatalog, bankFactory, goalCatalogHandler, goalOwnersHandler, goalRuleHandler, friendsHandler, categoryService):
        super().__init__(logerHandler, bankSlugsCatalog, bankFactory, goalCatalogHandler, goalOwnersHandler, goalRuleHandler, friendsHandler, categoryService)

    async def get_balance(self, userID: int) -> Dict[str, float]:
        balance = 0
        for slug in self.bankSlugsCatalog.all():
            bankHandler = self.bankFactory.get_handler(slug)
            slugTransactions = await bankHandler.get_data((bankHandler.dbt.userID == userID,))
            balance += sum([x.currencyAmount for x in slugTransactions])
        
        return {"data":balance}

    async def get_cash_flow(self, userID: int, period: str) -> List[Dict[str, Any]]:
        cashFlow: Dict[str, Dict[str, float]] = defaultdict(lambda: {"income": 0.0,"expense": 0.0,"net": 0.0,})

        for slug in self.bankSlugsCatalog.all():
            bankHandler = self.bankFactory.get_handler(slug)
            slugTransactions = await bankHandler.get_data(
                (bankHandler.dbt.userID == userID,)
            )

            for transaction in slugTransactions:
                operationDate = transaction.operationDate

                if isinstance(operationDate, datetime):
                    operationDate = operationDate.date()

                if not isinstance(operationDate, date):
                    continue
                
                match period:
                    case "day":
                        periodKey = operationDate.isoformat()

                    case "month":
                        periodKey = operationDate.strftime("%Y-%m")
    
                    case "year":
                        periodKey = operationDate.strftime("%Y")

                    case _:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unsupported period: {period}")

                amount = float(transaction.currencyAmount)

                if amount >= 0:
                    cashFlow[periodKey]["income"] += amount
                else:
                    cashFlow[periodKey]["expense"] += abs(amount)

                cashFlow[periodKey]["net"] += amount

        # готовим api-ответ
        result: List[Dict[str, Any]] = []
        for periodKey in sorted(cashFlow.keys()):
            item = cashFlow[periodKey]
            result.append({"period": periodKey,"income": round(item["income"], 2),"expense": round(item["expense"], 2),"net": round(item["net"], 2),})

        return result

    async def get_expense_category_distribution(self, userID: int) -> Dict[str, Any]:
        """
        Donut / Pie структура расходов по категориям.
        Берём транзакции из categoryService.get_transaction (возвращает dict),
        категория — поле "category" (строка), сумма — "currencyAmount".
        """

        slugs = ",".join(self.bankSlugsCatalog.all())
        print("slugs")
        response = await self.categoryService.get_transactions(
            slugs=slugs,
            userID=userID,
        )

        if response.get("status") != "success":
            return {
                "status": "error",
                "data": [],
                "meta": {
                    "reason": "categoryService.get_transaction failed",
                    "serviceMeta": response.get("meta"),
                },
            }

        transactions: List[Dict[str, Any]] = response.get("data") or []
        serviceMeta: Dict[str, Any] = response.get("meta") or {}

        categoryTotals: Dict[str, float] = defaultdict(float)
        totalExpense: float = 0.0

        for transaction in transactions:
            amount = float(transaction.get("currencyAmount") or 0)

            # учитываем только расходы
            if amount >= 0:
                continue

            expense = abs(amount)
            totalExpense += expense

            categoryName = transaction.get("category")
            if not categoryName:
                categoryName = "Прочие операции"

            categoryTotals[categoryName] += expense

        if totalExpense <= 0:
            return {
                "status": "success",
                "data": [],
                "meta": {
                    "totalExpense": 0.0,
                    "categories": 0,
                    "serviceMeta": serviceMeta,
                },
            }

        result: List[Dict[str, Any]] = []
        for categoryName, amount in sorted(categoryTotals.items(), key=lambda x: x[1], reverse=True):
            percent = (amount / totalExpense) * 100.0
            result.append({
                "category": categoryName,
                "amount": round(amount, 2),
                "percent": round(percent, 2),
            })

        return {
            "status": "success",
            "data": result,
            "meta": {
                "totalExpense": round(totalExpense, 2),
                "categories": len(result),
                "serviceMeta": serviceMeta,  # matchedCustom/unmatchedCustom и т.д.
            },
        }

    async def get_income_category_distribution(self, userID: int) -> Dict[str, Any]:
        """
        Donut / Pie структура доходов по категориям.
        """

        slugs = ",".join(self.bankSlugsCatalog.all())

        response = await self.categoryService.get_transactions(
            slugs=slugs,
            userID=userID,
        )

        if response.get("status") != "success":
            return {
                "status": "error",
                "data": [],
                "meta": {
                    "reason": "categoryService.get_transaction failed",
                    "serviceMeta": response.get("meta"),
                },
            }

        transactions: List[Dict[str, Any]] = response.get("data") or []
        serviceMeta: Dict[str, Any] = response.get("meta") or {}

        categoryTotals: Dict[str, float] = defaultdict(float)
        totalIncome: float = 0.0

        for transaction in transactions:
            amount = float(transaction.get("currencyAmount") or 0)

            # учитываем только доходы
            if amount <= 0:
                continue

            categoryName = transaction.get("category") or "Прочие операции"

            categoryTotals[categoryName] += amount
            totalIncome += amount

        if totalIncome <= 0:
            return {
                "status": "success",
                "data": [],
                "meta": {
                    "totalIncome": 0.0,
                    "categories": 0,
                    "serviceMeta": serviceMeta,
                },
            }

        result: List[Dict[str, Any]] = []
        for categoryName, amount in sorted(
            categoryTotals.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            percent = (amount / totalIncome) * 100.0
            result.append({
                "category": categoryName,
                "amount": round(amount, 2),
                "percent": round(percent, 2),
            })

        return {
            "status": "success",
            "data": result,
            "meta": {
                "totalIncome": round(totalIncome, 2),
                "categories": len(result),
                "serviceMeta": serviceMeta,
            },
        }


    async def get_last_transactions(self, userID: int, limit: int = 10) -> List[Dict[str, Any]]:
        # Последние пользовательские операции.
        return {}

    async def get_last_bank_transactions(self, userID: int, limit: int = 10) -> List[Dict[str, Any]]:
        # Последние операции, загруженные из банковских файлов.
        return {}

    # «УМНАЯ» АНАЛИТИКА (MVP)
    async def get_anomaly_transactions(self, userID: int) -> List[Dict[str, Any]]:
        # Нетипичные (аномальные) траты пользователя.
        return {}

    async def get_habits_cost(self, userID: int) -> List[Dict[str, Any]]:
        # Стоимость финансовых привычек (месяц / год).
        return {}

    async def get_user_financial_profile(self, userID: int) -> Dict[str, Any]:
        # Финансовый профиль пользователя (описательная аналитика).
        return {}

    # СКОРИНГ
    async def get_financial_health_score(self, userID: int) -> Dict[str, Any]:
        #Индекс финансового здоровья (0–100).
        return {}

    # ПРОГНОЗИРОВАНИЕ (PREDICTION)
    async def predict_next_month_expenses(self, userID: int) -> Dict[str, Any]:
        # Прогноз общих расходов на следующий месяц.
        return {}
    
    async def predict_category_expenses(self, userID: int) -> List[Dict[str, Any]]:
        # Прогноз расходов по категориям.
        return {}

