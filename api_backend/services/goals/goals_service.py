from typing import List, Dict
from abc import ABC, abstractmethod
from fastapi import HTTPException, status

from .schema import *

from ..users.schama import AuthUser

from ...handlers.db.orm_models.abstract_models import Operations

from ...handlers.logers.loger_handlers import LogerHandler
from ...handlers.friends.friends_handler import AbstractFriendsCatalogHandler
from ...handlers.goals.goals_rule_handler import AbstractGoalsRuleHandler
from ...handlers.goals.goals_catalog_handler import AbstractGoalsCatalogHandler
from ...handlers.goals.goals_owners_handler import AbstractGoalOwnersCatalogHandler


class AbstractGoalsService(ABC):
    @abstractmethod
    def __init__(self, logerHandler, goalsOwnersHandler, goalsCatalogHandler, goalsRulesHandler, friendsCatalogHandler):
        super().__init__()
        self.logerHandler: LogerHandler = logerHandler
        self.goalsCatalogHandler: AbstractGoalsCatalogHandler = goalsCatalogHandler
        self.goalsRulesHandler: AbstractGoalsRuleHandler = goalsRulesHandler
        self.goalsOwnersHandler: AbstractGoalOwnersCatalogHandler = goalsOwnersHandler
        self.friendsCatalogHandler: AbstractFriendsCatalogHandler = friendsCatalogHandler

    @abstractmethod
    def create_goal(self, userAuth: AuthUser, ceateGoalData: CreatGoal):
        pass


class GoalsService(AbstractGoalsService):
    def __init__(self, logerHandler, goalsOwnersHandler, goalsCatalogHandler, goalsRulesHandler, friendsCatalogHandler):
        super().__init__(logerHandler, goalsOwnersHandler,
                         goalsCatalogHandler, goalsRulesHandler, friendsCatalogHandler)


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


    async def get_goals(self, userAuth: AuthUser):
        goalsOwnersFiletr = (self.goalsOwnersHandler.dbt.userID == userAuth.get('id'),)
        goalsOwnersList = await self.goalsOwnersHandler.get_data(goalsOwnersFiletr)

        goalCatalogfilter = (self.goalsCatalogHandler.dbt.id.in_([x.goalID for x in goalsOwnersList]),)
        goalCatalog = await self.goalsCatalogHandler.get_data(goalCatalogfilter)

        return goalCatalog
