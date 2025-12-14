import os

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager

from app.screens.login_screen import LoginScreen
from app.screens.home_screen import HomeScreen
from app.services.api_client import ApiClient, ApiConfig
from app.services.session_service import SessionService
from app.screens.analytics_screen import AnalyticsScreen
from app.screens.collab_screen import CollabScreen

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
        Builder.load_file(os.path.join(baseAppPath, "kv", "collab_screen.kv"))

        screenManager = ScreenManager()
        
        screenManager.add_widget(HomeScreen(name="home", sessionService=self._sessionService))
        screenManager.add_widget(AnalyticsScreen(name="analytics"))
        screenManager.add_widget(CollabScreen(name="collab"))


        screenManager.add_widget(
            LoginScreen(
                name="login",
                apiClient=self._apiClient,
                sessionService=self._sessionService
            )
        )

        screenManager.add_widget(
            HomeScreen(
                name="home",
                sessionService=self._sessionService
            )
        )

        screenManager.current = "home" if self._sessionService.is_authorized() else "login"
        return screenManager