import os

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from app.screens.login_screen import LoginScreen
from app.screens.home_screen import HomeScreen
from app.services.api_client import ApiClient, ApiConfig
from app.services.session_service import SessionService
from app.screens.analytics_screen import AnalyticsScreen
from app.screens.transactions_screen import TransactionsScreen
from app.screens.transaction_details_screen import TransactionDetailsScreen
from app.screens.categories_screen import CategoriesScreen
from app.screens.category_create_screen import CategoryCreateScreen
from app.screens.transactions_upload_screen import TransactionsUploadScreen
from app.screens.manual_transaction_screen import ManualTransactionScreen
from app.screens.friends_screen import FriendsScreen
from app.screens.goals_catalog_screen import GoalsCatalogScreen 
from app.screens.goal_create_screen import GoalCreateScreen
from app.screens.goal_edit_screen import GoalEditScreen

class TallaryUiApp:
    def __init__(self) -> None:
        baseUrl = "http://localhost:8000"
        apiConfig = ApiConfig(baseUrl=baseUrl, timeoutSeconds=10)
        self._apiClient = ApiClient(apiConfig=apiConfig)

        baseAppPath = os.path.dirname(__file__)
        self._projectRootPath = baseAppPath

        sessionPath = os.path.join(baseAppPath, "app", "assets", "session.json")
        self._sessionService = SessionService(storagePath=sessionPath)
        self._sessionService.load()

    def build(self) -> ScreenManager:
        baseAppPath = os.path.dirname(__file__)

        Builder.load_file(os.path.join(baseAppPath, "kv", "login_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "home_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "analytics_screen.kv"))
        # Builder.load_file(os.path.join(baseAppPath, "kv", "collab_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "transactions_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "transaction_details_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "categories_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "category_create_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "transactions_upload_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "manual_transaction_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "friends_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "goals_catalog_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "goal_create_screen.kv"))
        Builder.load_file(os.path.join(baseAppPath, "kv", "goal_edit_screen.kv"))

        screenManager = ScreenManager()
        
        screenManager.add_widget(HomeScreen(name="home",apiClient=self._apiClient, sessionService=self._sessionService))
        # screenManager.add_widget(CollabScreen(name="collab"))
        screenManager.add_widget(LoginScreen(name="login", apiClient=self._apiClient, sessionService=self._sessionService))
        screenManager.add_widget(TransactionsScreen(name="transactions", apiClient=self._apiClient,  sessionService=self._sessionService,))
        screenManager.add_widget(TransactionDetailsScreen(name="transaction_details", apiClient=self._apiClient, sessionService=self._sessionService))
        screenManager.add_widget(CategoriesScreen(name="categories", apiClient=self._apiClient, sessionService=self._sessionService))
        screenManager.add_widget(CategoryCreateScreen(name="category_create", apiClient=self._apiClient, sessionService=self._sessionService))
        screenManager.add_widget(AnalyticsScreen(name="analytics", apiClient=self._apiClient, sessionService=self._sessionService,))
        screenManager.add_widget(TransactionsUploadScreen(name="transactions_upload"))
        screenManager.add_widget(ManualTransactionScreen(name="manual_transaction"))
        screenManager.add_widget(FriendsScreen(name="friends", apiClient=self._apiClient, sessionService=self._sessionService))
        screenManager.add_widget(GoalsCatalogScreen(name="goals", apiClient=self._apiClient, sessionService=self._sessionService))
        screenManager.add_widget(GoalCreateScreen(name="goal_create", apiClient=self._apiClient, sessionService=self._sessionService))
        screenManager.add_widget(GoalEditScreen(name="goal_edit",apiClient=self._apiClient,sessionService=self._sessionService))




        screenManager.current = "home" if self._sessionService.is_authorized() else "login"

        return screenManager