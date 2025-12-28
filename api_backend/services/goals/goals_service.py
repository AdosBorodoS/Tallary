from typing import List, Dict
from abc import ABC, abstractmethod
from fastapi import HTTPException, status
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List


from .schema import *

from ..users.schama import AuthUser

from ...handlers.db.orm_models.abstract_models import Operations

from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.friends.friends_handler import AbstractFriendsCatalogHandler
from ...handlers.goals.goals_rule_handler import AbstractGoalsRuleHandler
from ...handlers.goals.goals_catalog_handler import AbstractGoalsCatalogHandler
from ...handlers.goals.goals_owners_handler import AbstractGoalOwnersCatalogHandler
from ...handlers.goals.goal_transactions_link_handler import AbstractGoalsTransactionLinkHandler
from ...handlers.bank_files.bank_registry import BankHandlerRegistry
from ...handlers.bank_files.bank_slugs import BankSlugs

class AbstractGoalsService(ABC):
    @abstractmethod
    def __init__(self, logerHandler, goalsOwnersHandler, goalsCatalogHandler, goalsRulesHandler, friendsCatalogHandler, goalsTransactionLinkHandler, bankFabric, bankSlugs):
        super().__init__()
        self.logerHandler: LogerHandler = logerHandler
        self.goalsCatalogHandler: AbstractGoalsCatalogHandler = goalsCatalogHandler
        self.goalsRulesHandler: AbstractGoalsRuleHandler = goalsRulesHandler
        self.goalsOwnersHandler: AbstractGoalOwnersCatalogHandler = goalsOwnersHandler
        self.friendsCatalogHandler: AbstractFriendsCatalogHandler = friendsCatalogHandler
        self.goalsTransactionLinkHandler: AbstractGoalsTransactionLinkHandler = goalsTransactionLinkHandler
        self.bankFabric:BankHandlerRegistry = bankFabric
        self.bankSlugs:BankSlugs = bankSlugs


    @abstractmethod
    def create_goal(self, userAuth: AuthUser, ceateGoalData: CreatGoal):
        pass


class GoalsService(AbstractGoalsService):
    def __init__(self, logerHandler, goalsOwnersHandler, goalsCatalogHandler, goalsRulesHandler, friendsCatalogHandler, goalsTransactionLinkHandler, bankFabric, bankSlugs):
        super().__init__(logerHandler, goalsOwnersHandler, goalsCatalogHandler, goalsRulesHandler, friendsCatalogHandler, goalsTransactionLinkHandler, bankFabric, bankSlugs)

    async def _is_goal_exist(self, gaolID):
        goalCatalog = await self.goalsCatalogHandler.get_data((self.goalsCatalogHandler.dbt.id == gaolID,))
        return True if goalCatalog.__len__() else None

    async def _is_user_goal_exist(self, goalID, userID):
        ownersCatalog = await self.goalsOwnersHandler.get_data(
            (self.goalsOwnersHandler.dbt.userID == userID,
             self.goalsOwnersHandler.dbt.goalID == goalID,))
        return True if ownersCatalog.__len__() else None

    async def _raise_goal_existense(self, goalID:int, userID:int):
        if not await self._is_goal_exist(goalID):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
        
        if not await self._is_user_goal_exist(goalID=goalID, userID=userID):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User goal not found")


    async def create_goal(self, userAuth: AuthUser, ceateGoalData: CreatGoal):
        goalsCatalogItem = await self.goalsCatalogHandler.insert_data(goalName=ceateGoalData.goalName)
        goalsCatalogItem=goalsCatalogItem[0]
        
        goalsOwnersItemItem = await self.goalsOwnersHandler.insert_data(userID=userAuth.get('id'), goalID=goalsCatalogItem.get("id"))
        goalsOwnersItemItem = goalsOwnersItemItem[0]
        
        goalOperatorsPull = await self.add_goal_operator(goalsCatalogItem.get("id"), ceateGoalData.operators)
        
        return {"goal":goalsCatalogItem, 'owners':goalsOwnersItemItem, 'operators':goalOperatorsPull}

    async def delete_goal(self, userAuth: AuthUser, goalID:int):
        await self._raise_goal_existense(userID=userAuth.get('id'), goalID=goalID)
        
        goalsOwners = await self.goalsOwnersHandler.get_data((self.goalsOwnersHandler.dbt.goalID == goalID,))
        for owner in goalsOwners:
            await self.goalsOwnersHandler.delete_data(userID=owner.userID, goalID=goalID)


        goalsRuleCatalog = await self.goalsRulesHandler.get_data((self.goalsRulesHandler.dbt.goalID == goalID,))
        for goalsRule in goalsRuleCatalog:
            await self.goalsRulesHandler.delete_data(goalRuleID=goalsRule.id)

        await self.goalsCatalogHandler.delete_data(goalID=goalID)

        return {"status":True, "msg":"Goal deleted successfuly"}


    async def add_goal_participant(self, userAuth: AuthUser, participantCatalog:GaolParticipant):
        await self._raise_goal_existense(userID=userAuth.get('id'), goalID=participantCatalog.goalID)
        
        participantPull = []
        for participant in participantCatalog.participants:
            addParticipant = await self.goalsOwnersHandler.insert_data(goalID=participantCatalog.goalID, userID=participant.userID)
            participantPull.append(addParticipant[0])
        
        return {"status":True, "data":participantPull}

    async def delete_goal_participant(self, userAuth: AuthUser, participantCatalog:GaolParticipant):
        await self._raise_goal_existense(userID=userAuth.get('id'), goalID=participantCatalog.goalID)
        
        for participant in participantCatalog.participants:
            await self.goalsOwnersHandler.delete_data(userID=participant.userID,goalID=participantCatalog.goalID)        

        goalsOwners = await self.goalsOwnersHandler.get_data((self.goalsOwnersHandler.dbt.goalID == participantCatalog.goalID,))
        
        if goalsOwners.__len__():
            return {"status":True, "msg":"Participant deleted successfuly"}
        
        goalsRuleCatalog = await self.goalsRulesHandler.get_data((self.goalsRulesHandler.dbt.goalID == participantCatalog.goalID,))
        for goalsRule in goalsRuleCatalog:
            await self.goalsRulesHandler.delete_data(goalRuleID=goalsRule.id)

        await self.goalsCatalogHandler.delete_data(goalID=participantCatalog.goalID)

        return {"status":True, "msg":"Goal deleted successfuly"}
    
    async def get_goal_participant(self, goalID:int, userAuth: AuthUser):
        await self._raise_goal_existense(userID=userAuth.get('id'), goalID=goalID)

        getGoalOwnersFilter = (self.goalsOwnersHandler.dbt.goalID == goalID,)
        goalsOwners = await self.goalsOwnersHandler.get_data(getGoalOwnersFilter)

        getGoalOwnersNameFilter = (self.friendsCatalogHandler.userCatalogHandler.dbt.id.in_([x.userID for x in goalsOwners]),)
        getGoalOwnersName = await self.friendsCatalogHandler.userCatalogHandler.get_data(getGoalOwnersNameFilter)
        getGoalOwnersName = [x.to_dict() for x in getGoalOwnersName]

        for user in getGoalOwnersName:
            user.pop('password')



        return getGoalOwnersName





    async def add_goal_operator(self, goalID:int, operators:List[CreatGoalOperators]) -> List[Dict]:
        goalOperatorsPull = []
        for operator in operators:
            operatorItem = await self.goalsRulesHandler.insert_data(goalID=goalID,
                                                                    goalOperation=operator.goalOperator,
                                                                    goalRule=operator.goalRule)
            goalOperatorsPull.append(operatorItem[0])
        
        return goalOperatorsPull

    async def delete_gaol_operator(self, operatorID:int):
        return await self.goalsRulesHandler.delete_data(operatorID)

    async def get_goal_operator(self, goalID:int):
        getGoalOperatorFilter = (self.goalsRulesHandler.dbt.goalID == goalID,)
        return await self.goalsRulesHandler.get_data(getGoalOperatorFilter)

    async def get_goals(self, userAuth: AuthUser):
        goalsOwnersFiletr = (self.goalsOwnersHandler.dbt.userID == userAuth.get('id'),)
        goalsOwnersList = await self.goalsOwnersHandler.get_data(goalsOwnersFiletr)

        goalCatalogfilter = (self.goalsCatalogHandler.dbt.id.in_([x.goalID for x in goalsOwnersList]),)
        goalCatalog = await self.goalsCatalogHandler.get_data(goalCatalogfilter)

        return goalCatalog

    async def add_goal_transaction_link(self, userAuth: AuthUser, addTransactionData:AddGoalTransactionLink):
        if not addTransactionData.transactionSource in self.bankSlugs.all():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")
        
        return await self.goalsTransactionLinkHandler.insert_data(
                goalID = addTransactionData.goalID,
                transactionID = addTransactionData.transactionID,
                transactionSource = addTransactionData.transactionSource,
                contributorUserID = addTransactionData.contributorUserID)

    async def delete_goal_transaction_link(self, userAuth: AuthUser, deleteData:DeleteGoalTransactionLink):
        return await self.goalsTransactionLinkHandler.delete_data((self.goalsTransactionLinkHandler.dbt.transactionID == deleteData.transactionID,
                                                                   self.goalsTransactionLinkHandler.dbt.transactionSource == deleteData.slug))
    
    @staticmethod
    def _get_goal_summary_by_rules(
        transactions: Iterable[Dict[str, Any]],
        rules: Iterable[Dict[str, Any]],
        *,
        use_abs_amounts: bool = False,
    ) -> Dict[str, Any]:

        def _to_decimal(value: Any) -> Decimal:
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError) as exc:
                print('-ЮЮЮЮЮЮЮЮЮЮЮЮ')
                raise ValueError(f"Invalid numeric value: {value!r}") from exc

        def _normalize_operation(operation: str) -> str:
            opMap = {"=": "=="}
            opValue = (operation or "").strip()
            return opMap.get(opValue, opValue)

        def _rule_score(operation: str, currentValue: Decimal, targetValue: Decimal) -> Decimal:
            if targetValue == 0:
                if operation in ("<", "<="):
                    return Decimal("1") - (currentValue / Decimal("1"))
                if operation in (">", ">="):
                    return Decimal("1") + (currentValue / Decimal("1"))
                if operation == "==":
                    return Decimal("1") if currentValue == 0 else Decimal("-1")
                if operation == "!=":
                    return Decimal("1") if currentValue != 0 else Decimal("0")
                return Decimal("0")

            if operation in (">", ">="):
                return currentValue / targetValue

            if operation in ("<", "<="):
                exceedValue = currentValue - targetValue
                if exceedValue <= 0:
                    return Decimal("1")
                return Decimal("1") - (exceedValue / targetValue)

            if operation == "==":
                return Decimal("1") - (abs(currentValue - targetValue) / targetValue)

            if operation == "!=":
                return abs(currentValue - targetValue) / targetValue

            return Decimal("0")

        txList: List[Dict[str, Any]] = list(transactions)
        operationsCount = len(txList)

        amounts: List[Decimal] = []
        for tx in txList:
            amountValue = _to_decimal(tx.get("currencyAmount"))
            amounts.append(abs(amountValue) if use_abs_amounts else amountValue)

        currentValue = sum(amounts, Decimal("0"))

        userTotals: Dict[str, Decimal] = {}
        for tx in txList:
            userName = str(tx.get("userName"))
            amountValue = _to_decimal(tx.get("currencyAmount"))
            amountValue = abs(amountValue) if use_abs_amounts else amountValue
            userTotals[userName] = userTotals.get(userName, Decimal("0")) + amountValue

        contributorsTotal = sum(userTotals.values(), Decimal("0"))

        contributorsBreakdown: List[Dict[str, Any]] = []
        for userName, userAmount in sorted(userTotals.items(), key=lambda x: x[1], reverse=True):
            shareValue = Decimal("0")
            sharePercentValue = Decimal("0")
            if contributorsTotal != 0:
                shareValue = userAmount / contributorsTotal
                sharePercentValue = shareValue * Decimal("100")

            contributorsBreakdown.append(
                {
                    "userName": userName,
                    "amount": float(userAmount),
                    "share": float(shareValue),
                    "sharePercent": float(sharePercentValue),   
                }
            )

        ruleScores: List[Decimal] = []
        rulesList = list(rules)

        for rule in rulesList:
            operation = _normalize_operation(str(rule.get("goalOperation")))
            targetValue = _to_decimal(rule.get("goalRule"))
            ruleScores.append(_rule_score(operation, currentValue, targetValue))

        completionRatio = min(ruleScores) if ruleScores else Decimal("0")
        completionPercent = completionRatio * Decimal("100")

        return {
            "currentValue": float(currentValue),
            "completionRatio": float(completionRatio),
            "completionPercent": float(completionPercent),
            "operationsCount": operationsCount,
            "contributorsTotal": float(contributorsTotal),
            "contributorsBreakdown": contributorsBreakdown,
            "ruleScores": [
                {
                    "goalOperation": _normalize_operation(str(r.get("goalOperation"))),
                    "goalRule": float(_to_decimal(r.get("goalRule"))),
                    "score": float(s),
                }
                for r, s in zip(rulesList, ruleScores)
            ],
        }

    async def get_goal_transactions(self, userAuth: AuthUser, goalID: int):
        # 1) Друзья + сам пользователь
        filterFriend = (self.friendsCatalogHandler.dbt.userID == userAuth.get("id"),)
        friendsPull = await self.friendsCatalogHandler.get_friend(filterFriend)

        friendsIdPull = [x.friendID for x in friendsPull]
        allowedUserIds = friendsIdPull + [userAuth.get("id")]

        # 2) Линки транзакций к цели
        filterValue = (
            self.goalsTransactionLinkHandler.dbt.contributorUserID.in_(allowedUserIds),
            self.goalsTransactionLinkHandler.dbt.goalID == goalID,
        )
        goalTransactionPull = await self.goalsTransactionLinkHandler.get_data(filterValue)

        reachTransactionsCatalog = []

        # 3) Собираем транзакции
        for goalTransaction in goalTransactionPull:
            txSource = goalTransaction.transactionSource
            if txSource not in self.bankSlugs.all():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")

            bankHandler = self.bankFabric.get_handler(txSource)

            ownerPull = await self.friendsCatalogHandler.userCatalogHandler.get_data(
                (self.friendsCatalogHandler.userCatalogHandler.dbt.id == goalTransaction.contributorUserID,)
            )
            if not ownerPull:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction owner not found")
            transactionOwner = ownerPull[0]

            txPull = await bankHandler.get_data((bankHandler.dbt.id == goalTransaction.transactionID,))
            if not txPull:
                # Если линк есть, а транзакции нет — это уже рассинхрон БД.
                # Можно либо пропускать, либо кидать 404/409. Я бы кидал 409.
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Linked transaction not found")
            transaction = txPull[0]

            reachTransactionsCatalog.append(
                {
                    "goalTransactionID": goalTransaction.id,
                    "userName": transactionOwner.userName,
                    "currencyAmount": transaction.currencyAmount,
                    "operationDate": transaction.operationDate,
                }
            )

        # 4) Правила цели
        goalRuleFilter = (self.goalsRulesHandler.dbt.goalID == goalID,)
        goalsRule = await self.goalsRulesHandler.get_data(goalRuleFilter)
        rulesList = [x.to_dict() for x in goalsRule]

        # 5) Метаданные: считаем один раз, даже если транзакций нет
        metadata = self._get_goal_summary_by_rules(reachTransactionsCatalog, rulesList)

        return {"transactions": reachTransactionsCatalog, "metadata": metadata}

    async def get_transaction_goal(self, transactionID:int, slug:str):
        filterTransactions = (self.goalsTransactionLinkHandler.dbt.transactionID == transactionID,
                              self.goalsTransactionLinkHandler.dbt.transactionSource == slug)
        transactionData = await self.goalsTransactionLinkHandler.get_data(filterTransactions)
        if transactionData.__len__():
            
            goalData = await self.goalsCatalogHandler.get_data((self.goalsCatalogHandler.dbt.id == transactionData[0].goalID,))
            return goalData
        return []