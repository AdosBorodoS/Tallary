from abc import ABC, abstractmethod
from collections import Counter,defaultdict
from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
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

        result: List[Dict[str, Any]] = []
        for periodKey in sorted(cashFlow.keys()):
            item = cashFlow[periodKey]
            result.append({"period": periodKey,"income": round(item["income"], 2),"expense": round(item["expense"], 2),"net": round(item["net"], 2),})

        return result

    async def get_expense_category_distribution(self, userID: int) -> Dict[str, Any]:
        response = await self.categoryService.get_transactions(
            slugs=",".join(self.bankSlugsCatalog.all()),
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
                "serviceMeta": serviceMeta,
            },
        }

    async def get_income_category_distribution(self, userID: int) -> Dict[str, Any]:
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

    async def get_last_transactions(self, userID: int, limit: int = 10) -> Dict[str, Any]:
        transactionsPull = {}
        for slug in self.bankSlugsCatalog.all():
            bankHandler = self.bankFactory.get_handler(slug)
            slugTransactions = await bankHandler.get_data((bankHandler.dbt.userID == userID,))
            slugTransactions = sorted(slugTransactions, key=lambda x: x.operationDate, reverse=True)
            transactionsPull.update({slug:slugTransactions[:limit]})

        return transactionsPull

    @staticmethod
    def _find_most_anomalous_expense(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        expenses = [t for t in transactions if t.get("currencyAmount", 0) < 0]
        if not expenses:
            return None

        from collections import defaultdict
        categories = defaultdict(list)
        for t in expenses:
            cat = t.get("category") or "Без категории"
            categories[cat].append(t)

        anomaliesWithScore = []

        for _, transList in categories.items():
            if len(transList) < 3:
                continue

            amounts = [abs(t["currencyAmount"] if "currencyAmount" in t else t["currencyAmount"]) for t in transList]

            amountsSorted = sorted(amounts)
            n = len(amountsSorted)
            q1 = amountsSorted[int(0.25 * (n - 1))]
            q3 = amountsSorted[int(0.75 * (n - 1))]
            iqr = q3 - q1
            threshold = q3 + 1.5 * iqr

            for t in transList:
                amount = abs(t["currencyAmount"])
                if amount > threshold:
                    score = amount - threshold
                    anomaliesWithScore.append((score, t))

        if not anomaliesWithScore:
            return {"status":False}

        _, mostAnomalous = max(anomaliesWithScore, key=lambda x: x[0])
        return {"status":True, "data":mostAnomalous}

    async def get_anomaly_transactions(self, userID: int) -> List[Dict[str, Any]]:
        slugs = ','.join(self.bankSlugsCatalog.all())
        transactionsPull = await self.categoryService.get_transactions(slugs=slugs, userID=userID)
        anomalyTransaction = self._find_most_anomalous_expense(transactionsPull.get("data"))
        return anomalyTransaction

    @staticmethod
    def _calculate_habit_cost(transactions: List[Dict[str, Any]]) -> Dict[str, float]:
        today = datetime(2025, 12, 22)
        sixMonthsAgo = today - timedelta(days=180)

        expenses = []
        for t in transactions:
            amount = t.get("currencyAmount")
            if amount is None or amount >= 0:
                continue

            try:
                opDate = datetime.strptime(t["operationDate"], "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            if opDate < sixMonthsAgo or opDate > today:
                continue

            category = t.get("category") or "Без категории"
            expenses.append({
                "category": category,
                "amount": abs(amount)
            })

        # from collections import defaultdict
        categoryTotals = defaultdict(float)
        categoryCounts = defaultdict(int)

        for exp in expenses:
            cat = exp["category"]
            categoryTotals[cat] += exp["amount"]
            categoryCounts[cat] += 1

        habitCosts = {
            cat: round(total, 2)
            for cat, total in categoryTotals.items()
            if categoryCounts[cat] >= 2
        }

        return habitCosts

    async def get_habits_cost(self, userID: int) -> List[Dict[str, Any]]:
        slugs = ','.join(self.bankSlugsCatalog.all())
        transactionsPull = await self.categoryService.get_transactions(slugs=slugs, userID=userID)
        habitsCost = self._calculate_habit_cost(transactionsPull.get("data"))
        return habitsCost

    @staticmethod
    def _generate_financial_profile(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not transactions:
            return {
                "profileSummary": "Недостаточно данных для построения финансового профиля.",
                "spendingStyle": "Не определён",
                "riskLevel": "неизвестно",
                "topCategories": [],
                "incomeToExpenseRatio": 0.0,
                "recommendations": ["Добавьте больше транзакций для анализа."]
            }

        totalIncome = 0.0
        totalExpense = 0.0
        expenseTransactions = []
        categoryCounter = Counter()

        for t in transactions:
            amount = t.get("currencyAmount")
            if amount is None:
                continue

            if amount > 0:
                totalIncome += amount
            elif amount < 0:
                expense = abs(amount)
                totalExpense += expense
                expenseTransactions.append(t)
                category = t.get("category") or "Без категории"
                categoryCounter[category] += 1

        incomeToExpenseRatio = round(totalIncome / totalExpense, 2) if totalExpense > 0 else float('inf')
        topCategories = [cat for cat, _ in categoryCounter.most_common(3)]

        if not expenseTransactions:
            spendingStyle = "Не тратит (или данные только о доходах)"
        elif any("Прочие операции" == (t.get("category") or "") for t in expenseTransactions) and len(expenseTransactions) > 5:
            if totalExpense > totalIncome * 0.9:
                spendingStyle = "Импульсивный тратильщик"
            else:
                spendingStyle = "Спонтанный, но осторожный"
        elif len([t for t in expenseTransactions if abs(t["currencyAmount"]) < 500]) > len(expenseTransactions) * 0.6:
            spendingStyle = "Микротратильщик (много мелочи)"
        elif "На квартиру" in topCategories or "Продукты" in topCategories:
            if incomeToExpenseRatio >= 1.3:
                spendingStyle = "Планирующий и ответственный"
            else:
                spendingStyle = "Бюджетник под давлением"
        else:
            spendingStyle = "Нестандартный профиль"

        if totalIncome == 0:
            riskLevel = "высокий"
        elif totalExpense > totalIncome * 0.95:
            riskLevel = "высокий"
        elif totalExpense > totalIncome * 0.75:
            riskLevel = "средний"
        else:
            riskLevel = "низкий"

        recommendations = []

        if riskLevel == "высокий":
            recommendations.append("Вы тратите почти весь доход. Создайте финансовую подушку.")
        if "Прочие операции" in categoryCounter and categoryCounter["Прочие операции"] > len(expenseTransactions) * 0.4:
            recommendations.append("Уточните категории расходов — это поможет лучше контролировать бюджет.")
        if len([t for t in expenseTransactions if abs(t["currencyAmount"]) < 300]) > 5:
            recommendations.append("Множество мелких трат тянут бюджет. Попробуйте недельный лимит на мелочи.")
        if incomeToExpenseRatio >= 1.5 and totalExpense > 0:
            recommendations.append("Вы отлично управляете финансами! Подумайте об инвестициях или целях.")
        if not recommendations:
            recommendations.append("Продолжайте в том же духе — вы на правильном пути.")

        if totalIncome == 0 and totalExpense == 0:
            summary = "Активность в транзакциях минимальна. Невозможно оценить профиль."
        elif totalIncome == 0:
            summary = "Обнаружены только расходы. Источник средств неизвестен — возможен риск долговой нагрузки."
        elif totalExpense == 0:
            summary = "Только поступления средств. Расходы не зафиксированы — возможно, используется другой счёт."
        else:
            ratioDesc = (
                "тратит значительно меньше, чем зарабатывает" if incomeToExpenseRatio >= 1.5 else
                "тратит почти весь доход" if incomeToExpenseRatio <= 1.05 else
                "сохраняет умеренный баланс между доходами и расходами"
            )
            styleDesc = f"Стиль трат: {spendingStyle.lower()}."
            riskDesc = f"Уровень финансового риска: {riskLevel}."
            summary = f"Пользователь {ratioDesc}. {styleDesc} {riskDesc}"

        return {
            "profileSummary": summary,
            "spendingStyle": spendingStyle,
            "riskLevel": riskLevel,
            "topCategories": topCategories,
            "incomeToExpenseRatio": incomeToExpenseRatio if incomeToExpenseRatio != float('inf') else 0.0,
            "recommendations": recommendations
        }

    async def get_user_financial_profile(self, userID: int) -> Dict[str, Any]:
        slugs = ','.join(self.bankSlugsCatalog.all())
        transactionsPull = await self.categoryService.get_transactions(slugs=slugs, userID=userID)
        return self._generate_financial_profile(transactionsPull.get('data'))
    
    @staticmethod
    def _calculate_financial_literacy_score(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not transactions:
            return {"score": 0, "category": "Финансовая бестолочь"}

        income = 0.0
        expenses = 0.0
        categoryCounter = []
        otherCategoryCount = 0
        essentialCategories = {"На квартиру", "Продукты", "Здоровье", "Транспорт", "Коммунальные услуги", "Еда"}
        essentialExpenses = 0.0

        for t in transactions:
            amount = t.get("currencyAmount")
            if amount is None:
                continue

            if amount > 0:
                income += amount
            elif amount < 0:
                expense = abs(amount)
                expenses += expense
                categoryCounter.append(t)

                category = t.get("category", "Прочие операции") or "Прочие операции"
                if category == "Прочие операции":
                    otherCategoryCount += 1

                if category in essentialCategories:
                    essentialExpenses += expense

        if income == 0:
            balanceScore = 0
        else:
            expenseRatio = expenses / income
            if expenseRatio <= 0.7:
                balanceScore = 40
            elif expenseRatio <= 1.0:
                balanceScore = int(40 * (1 - (expenseRatio - 0.7) / 0.3))
            else:
                balanceScore = max(0, int(40 * (1 / expenseRatio)))

        smallExpenses = sum(1 for t in categoryCounter if abs(t["currencyAmount"]) < 1000)
        if len(categoryCounter) == 0:
            habitScore = 20
        else:
            smallRatio = smallExpenses / len(categoryCounter)
            habitScore = int(20 * (1 - min(smallRatio, 1.0)))

        if len(categoryCounter) == 0:
            categorization_score = 15
        else:
            other_ratio = otherCategoryCount / len(categoryCounter)
            categorization_score = int(15 * (1 - min(other_ratio, 1.0)))
        if expenses == 0:
            essentialScore = 0
        else:
            essential_ratio = essentialExpenses / expenses
            if 0.5 <= essential_ratio <= 0.7:
                essentialScore = 25
            elif essential_ratio < 0.3:
                essentialScore = int(25 * (essential_ratio / 0.3))
            elif essential_ratio > 0.9:
                essentialScore = int(25 * (1 - (essential_ratio - 0.7) / 0.2))
            else:
                essentialScore = max(0, int(25 * (1 - abs(essential_ratio - 0.6) / 0.2)))

        totalScore = balanceScore + habitScore + categorization_score + essentialScore
        totalScore = max(0, min(100, totalScore))

        if totalScore <= 30:
            category = "Финансовая бестолочь"
        elif totalScore <= 50:
            category = "Новичок в деньгах"
        elif totalScore <= 75:
            category = "Осознанный тратильщик"
        elif totalScore <= 90:
            category = "Финансовый стратег"
        else:
            category = "Финансовый гений"

        return {
            "score": totalScore,
            "category": category
        }

    # СКОРИНГ
    async def get_financial_health_score(self, userID: int) -> Dict[str, Any]:
        slugs = ','.join(self.bankSlugsCatalog.all())
        transactionsPull = await self.categoryService.get_transactions(slugs=slugs, userID=userID)
        return self._calculate_financial_literacy_score(transactionsPull.get('data'))
    
    @staticmethod
    def _forecast_next_month_expenses(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not transactions:
            return {
                "forecastAmount": 0.0,
                "confidence": "низкая",
                "periodsAnalyzed": 0,
                "message": "Недостаточно данных для прогноза."
            }

        today = datetime(2025, 12, 22)
        currentMonth = today.year * 12 + today.month

        monthlyExpenses = defaultdict(float)

        for t in transactions:
            amount = t.get("currencyAmount")
            if amount is None or amount >= 0:
                continue

            try:
                opDate = datetime.strptime(t["operationDate"], "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            monthKey = opDate.year * 12 + opDate.month
            if monthKey > currentMonth:
                continue 
            if monthKey < currentMonth - 5:
                continue

            monthlyExpenses[monthKey] += abs(amount)

        sortedMonths = sorted(monthlyExpenses.items())
        if not sortedMonths:
            return {
                "forecastAmount": 0.0,
                "confidence": "низкая",
                "periodsAnalyzed": 0,
                "message": "Расходы не обнаружены."
            }

        expenseValues = [v for _, v in sortedMonths]
        n = len(expenseValues)

        if n == 1:
            forecast = expenseValues[0]
            confidence = "низкая"
        elif n <= 3:
            forecast = sum(expenseValues) / n
            confidence = "средняя"
        else:
            t = list(range(n))
            y = expenseValues

            meanT = sum(t) / n
            meanY = sum(y) / n

            numerator = sum((ti - meanT) * (yi - meanY) for ti, yi in zip(t, y))
            denominator = sum((ti - meanT) ** 2 for ti in t)

            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator

            intercept = meanY - slope * meanT

            forecast = slope * n + intercept
            forecast = max(0, forecast)
            confidence = "высокая" if n >= 5 else "средняя"

        return {
            "forecastAmount": round(forecast, 2),
            "confidence": confidence,
            "periodsAnalyzed": n,
            "message": f"Прогноз основан на данных за {n} {'месяц' if n == 1 else 'месяца' if 2 <= n <= 4 else 'месяцев'}."
        }
    
    # ПРОГНОЗИРОВАНИЕ (PREDICTION)
    async def predict_next_month_expenses(self, userID: int) -> Dict[str, Any]:
        slugs = ','.join(self.bankSlugsCatalog.all())
        transactionsPull = await self.categoryService.get_transactions(slugs=slugs, userID=userID)
        return self._forecast_next_month_expenses(transactionsPull.get('data'))

    @staticmethod
    def _forecast_expenses_by_category(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not transactions:
            return {
                "forecastByCategory": {},
                "totalForecast": 0.0,
                "confidence": "низкая",
                "message": "Недостаточно данных для прогноза по категориям."
            }

        today = datetime(2025, 12, 22)
        currentmonthKey = today.year * 12 + today.month

        categoryMonthly = defaultdict(lambda: defaultdict(float))

        for t in transactions:
            amount = t.get("currencyAmount")
            if amount is None or amount >= 0:
                continue

            try:
                opDate = datetime.strptime(t["operationDate"], "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            monthKey = opDate.year * 12 + opDate.month
            if monthKey > currentmonthKey or monthKey < currentmonthKey - 5:
                continue

            category = t.get("category") or "Без категории"
            categoryMonthly[category][monthKey] += abs(amount)

        if not categoryMonthly:
            return {
                "forecastByCategory": {},
                "totalForecast": 0.0,
                "confidence": "низкая",
                "message": "Расходы не обнаружены."
            }

        forecastByCategory = {}
        totalForecast = 0.0
        totalMonthsObserved = 0

        ALPHA = 0.6

        for category, monthlyData in categoryMonthly.items():
            monthsSorted = sorted(monthlyData.items())
            amounts = [amt for _, amt in monthsSorted]
            n = len(amounts)
            totalMonthsObserved += n

            if n == 1:
                forecast = amounts[0]
                conf = 1
            elif n == 2:
                forecast = sum(amounts) / 2
                conf = 2
            else:
                smoothed = amounts[0]
                for i in range(1, n):
                    smoothed = ALPHA * amounts[i] + (1 - ALPHA) * smoothed
                forecast = smoothed
                conf = 3

            forecast = max(0, round(forecast, 2))
            forecastByCategory[category] = forecast
            totalForecast += forecast

        avgMonthsPerCat = totalMonthsObserved / len(categoryMonthly)
        if avgMonthsPerCat >= 3:
            confidence = "высокая"
        elif avgMonthsPerCat >= 2:
            confidence = "средняя"
        else:
            confidence = "низкая"

        return {
            "forecastByCategory": forecastByCategory,
            "totalForecast": round(totalForecast, 2),
            "confidence": confidence,
            "message": f"Прогноз по {len(forecastByCategory)} категориям. Уровень уверенности: {confidence}."
        }
    
    async def predict_category_expenses(self, userID: int) -> List[Dict[str, Any]]:
        slugs = ','.join(self.bankSlugsCatalog.all())
        transactionsPull = await self.categoryService.get_transactions(slugs=slugs, userID=userID)
        return self._forecast_expenses_by_category(transactionsPull.get('data'))


