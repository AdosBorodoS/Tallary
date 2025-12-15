from abc import ABC, abstractmethod


class AbstractGoalsService(ABC):
    @abstractmethod
    def __init__(self,goalsCatalogHandler, goalsRulesHandler, friendsCatalogHandler):
        super().__init__()
        self.goalsCatalogHandler = goalsCatalogHandler
        self.goalsRulesHandler = goalsRulesHandler
        self.friendsCatalogHandler = friendsCatalogHandler

    @abstractmethod
    def create_goal(self):
        pass

    @abstractmethod
    def get_user_goals(self):
        pass

    @abstractmethod
    def update_goal(self):
        pass

    @abstractmethod
    def delete_goal(self):
        pass

    @abstractmethod
    def get_coop_goals(self):
        pass