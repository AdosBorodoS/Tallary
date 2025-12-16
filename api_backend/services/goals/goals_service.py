from typing import List, Dict
from abc import ABC, abstractmethod
from fastapi import HTTPException, status

from .schema import CreatGoal, CreatColabGoal, AddGoalOwner, CreatGoalOperators

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

    async def create_goal(self, userAuth: AuthUser, ceateGoalData: CreatGoal):
        goalsCatalogItem = await self.goalsCatalogHandler.insert_data(goalName=ceateGoalData.goalName)
        goalsCatalogItem=goalsCatalogItem[0]
        
        addGoalOwner = AddGoalOwner(goalID=goalsCatalogItem.get("id"), friendIDs=[userAuth.get('id')])
        goalsOwnersItemItem = await self.add_goal_owner(userAuth, addGoalOwner)
        goalsOwnersItemItem = goalsOwnersItemItem[0]
        
        goalOperatorsPull = await self.add_goal_operator(goalsCatalogItem.get("id"), ceateGoalData.operators)
        
        return {"goal":goalsCatalogItem, 'owners':goalsOwnersItemItem, 'operators':goalOperatorsPull}

    async def create_colab_goal(self, userAuth: AuthUser, ceateColabGoalData: CreatColabGoal):
        goalsCatalogItem = await self.goalsCatalogHandler.insert_data(goalName=ceateColabGoalData.goalName)
        goalsCatalogItem = goalsCatalogItem[0]

        addGoalOwner = AddGoalOwner(goalID=goalsCatalogItem.get("id"),friendIDs=ceateColabGoalData.friendIDs + [userAuth.get('id')])
        goalsOwnersPull = await self.add_goal_owner(userAuth, addGoalOwner)

        goalOperatorsPull = await self.add_goal_operator(goalsCatalogItem.get("id"), ceateColabGoalData.operators)

        # goalOperatorsPull = []
        # for operator in ceateColabGoalData.operators:
        #     operatorItem = await self.goalsRulesHandler.insert_data(goalID=goalsCatalogItem.get("id"),
        #                                                             goalOperation=operator.goalOperator,
        #                                                             goalRule=operator.goalRule)
        #     goalOperatorsPull.append(operatorItem[0])

        return {"goal":goalsCatalogItem,'owners':goalsOwnersPull,'operators':goalOperatorsPull}


    async def add_goal_owner(self, userAuth: AuthUser, addGoalOwnerData: AddGoalOwner) -> List[Dict]:
        
        goalsOwnersPull = []
        for goalOwnerID in addGoalOwnerData.friendIDs:
            if await self.friendsCatalogHandler._user_is_exist(goalOwnerID) and await self.friendsCatalogHandler._user_is_friend(userAuth.get('id'), goalOwnerID):
                goalOwners = await self.goalsOwnersHandler.insert_data(userID=goalOwnerID, goalID=addGoalOwnerData.goalID)
                goalsOwnersPull.append(goalOwners[0])

        return goalsOwnersPull

    async def add_goal_operator(self, goalID:int, operators:List[CreatGoalOperators]) -> List[Dict]:
        goalOperatorsPull = []
        for operator in operators:
            operatorItem = await self.goalsRulesHandler.insert_data(goalID=goalID,
                                                                    goalOperation=operator.goalOperator,
                                                                    goalRule=operator.goalRule)
            goalOperatorsPull.append(operatorItem[0])
        
        return goalOperatorsPull


    async def get_goals(self, userAuth: AuthUser):
        goalsOwnersFiletr = (self.goalsOwnersHandler.dbt.userID == userAuth.get('id'),)
        goalsOwnersList = await self.goalsOwnersHandler.get_data(goalsOwnersFiletr)

        goalCatalogfilter = (self.goalsCatalogHandler.dbt.id.in_([x.goalID for x in goalsOwnersList]),)
        goalCatalog = await self.goalsCatalogHandler.get_data(goalCatalogfilter)

        return goalCatalog


    async def _is_last_owner(self, goalID:int)-> bool:
        getLastFilter = (self.goalsOwnersHandler.dbt.goalID == goalID,)
        data = await self.goalsOwnersHandler.get_data(getLastFilter)
        if data.__len__()<=1:
            return True
        return False

    async def delete_goal_owner(self, userAuth: AuthUser, goalID:int): 
        if self._is_last_owner(goalID):
            deleteData = await self.goalsCatalogHandler.delete_data(goalID=goalID)

        deleteOwner = await self.goalsOwnersHandler.delete_data(userID=userAuth.get('id'), goalID=goalID)
        return deleteOwner


    async def delete_goal_operator(self, goalRuleID:int):
        return await self.goalsRulesHandler.delete_data(goalRuleID)

    async def delete_goal(self,goalID: int):
        return await self.goalsCatalogHandler.delete_data(goalID)
