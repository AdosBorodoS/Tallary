from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

from app.services.session_service import SessionService
from app.widgets.bottom_nav_mixin import BottomNavMixin


class HomeScreen(BottomNavMixin, Screen):
    userNameText = StringProperty("")

    def __init__(self, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sessionService = sessionService

    def on_pre_enter(self, *args) -> None:
        self.userNameText = self._sessionService.get_user_name() or ""
        super().on_pre_enter(*args)

    def on_import_statements_button_click(self) -> None:
        print("Import statements clicked")

    def on_add_transaction_button_click(self) -> None:
        print("Add transaction clicked")

    def on_logout_button_click(self) -> None:
        self._sessionService.clear()
        self.manager.current = "login"
