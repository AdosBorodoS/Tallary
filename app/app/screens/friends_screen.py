from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.widgets.bottom_nav_mixin import BottomNavMixin


class FriendsScreen(BottomNavMixin, Screen):
    titleText = StringProperty("Друзья")

    searchText = StringProperty("")
    statusText = StringProperty("")
    usersEmptyText = StringProperty("")

    isLoading = BooleanProperty(False)

    friendsData = ListProperty([])
    usersData = ListProperty([])

    selectedUserId = NumericProperty(0)
    selectedUserName = StringProperty("")

    selectedFriendId = NumericProperty(0)
    selectedFriendName = StringProperty("")

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._allFriends: list[dict] = []
        self._allUsers: list[dict] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_lists()

    # ---------- UI handlers ----------
    def on_back_button_click(self) -> None:
        self.on_nav_click("home")

    def on_search_button_click(self) -> None:
        query = (self.searchText or "").strip()
        print(f"[FriendsScreen] search query='{query}'")
        self._apply_users_search()

    def on_friend_row_click(self, userId: int, userName: str) -> None:
        self.selectedFriendId = int(userId)
        self.selectedFriendName = str(userName)
        self.statusText = f"Выбран друг: {self.selectedFriendName}"

    def on_user_row_click(self, userId: int, userName: str) -> None:
        self.selectedUserId = int(userId)
        self.selectedUserName = str(userName)
        self.statusText = f"Выбран пользователь: {self.selectedUserName}"

    def on_add_friend_button_click(self) -> None:
        if self.selectedUserId <= 0:
            self.statusText = "Сначала выбери пользователя из списка ниже"
            return

        # Пока заглушка: просто выводим id в консоль
        print(f"[FriendsScreen] add friend userId={self.selectedUserId}")

        # Позже будет API вызов
        # self._run_request_in_thread(
        #     request_func=lambda: self._apiClient.add_friend(self.selectedUserId),
        #     on_success=lambda _: self._load_lists(),
        #     on_error=self._handle_error,
        # )

    def on_goals_button_click(self) -> None:
        self.on_nav_click("goals")

    # ---------- Loading ----------
    def _load_lists(self) -> None:
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Загрузка..."
        self.friendsData = []
        self.usersData = []
        self.selectedUserId = 0
        self.selectedUserName = ""

        self._run_request_in_thread(
            request_func=self._fetch_payload_placeholder,
            on_success=self._apply_payload,
            on_error=self._handle_error,
        )

    def _fetch_payload_placeholder(self) -> dict:
        """
        Заглушка под API:

        friends endpoint -> list[{"id": int, "userName": str}]
        users endpoint   -> {"data": list[{"id": int, "userName": str}]}
        """
        friends = [
            {"id": 2, "userName": "user1"},
        ]
        users = {
            "data": [
                {"id": 1, "userName": "admin"},
                {"id": 2, "userName": "user1"},
                {"id": 3, "userName": ""},       # пример: нет ника -> НЕ покажем
                {"id": 4, "userName": None},     # пример: нет ника -> НЕ покажем
            ]
        }
        return {"friends": friends, "users": users}

    def _apply_payload(self, result: Any) -> None:
        self.isLoading = False

        if not isinstance(result, dict):
            self.statusText = "Некорректный ответ"
            return

        friendsRaw = result.get("friends")
        usersRaw = result.get("users")

        self._allFriends = self._normalize_people_list(raw=friendsRaw, listKey=None)
        self._allUsers = self._normalize_people_list(raw=usersRaw, listKey="data")

        self.friendsData = self._build_rv_data(self._allFriends, rowType="friend")
        self._apply_users_search()

        self.statusText = ""

    def _normalize_people_list(self, raw: Any, listKey: Optional[str]) -> list[dict]:
        if listKey is None:
            items = raw
        else:
            items = raw.get(listKey) if isinstance(raw, dict) else None

        if not isinstance(items, list):
            return []

        normalized: list[dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            personId = item.get("id")
            userName = item.get("userName")

            if personId is None:
                continue

            # Важно: показываем ТОЛЬКО то, что реально пришло как userName.
            # Если ника нет/пусто -> вообще не выводим строку.
            if not isinstance(userName, str):
                continue

            userNameValue = userName.strip()
            if not userNameValue:
                continue

            try:
                normalized.append({"id": int(personId), "userName": userNameValue})
            except Exception:
                continue

        return normalized

    def _build_rv_data(self, items: list[dict], rowType: str) -> list[dict]:
        rv: list[dict] = []
        for item in items:
            rv.append(
                {
                    "screen": self,
                    "rowType": rowType,
                    "userId": int(item["id"]),
                    "userName": str(item["userName"]),
                }
            )
        return rv

    def on_remove_friend_button_click(self) -> None:
        if self.selectedFriendId <= 0:
            self.statusText = "Сначала выбери друга"
            return

        # Заглушка — просто выводим id
        print(f"[FriendsScreen] remove friend userId={self.selectedFriendId}")



    def _apply_users_search(self) -> None:
        query = (self.searchText or "").strip().lower()

        if not query:
            filtered = self._allUsers
        else:
            filtered = []
            for item in self._allUsers:
                if query in str(item.get("userName") or "").lower():
                    filtered.append(item)

        self.usersData = self._build_rv_data(filtered, rowType="user")

        if query and len(filtered) == 0:
            self.usersEmptyText = "Ничего не найдено"
        else:
            self.usersEmptyText = ""

    # ---------- errors / threading ----------
    def _handle_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False
        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()
        self.statusText = f"Ошибка: {detail}" if detail else "Ошибка загрузки"
        self.friendsData = []
        self.usersData = []

    def _safe_extract_response_payload(self, response: Optional[requests.Response]) -> Any:
        if response is None:
            return {"detail": "No response"}
        try:
            return response.json()
        except Exception:
            textValue = (response.text or "").strip()
            return {"detail": textValue} if textValue else {"detail": f"HTTP {response.status_code}"}

    def _run_request_in_thread(
        self,
        request_func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Optional[int], Any], None],
    ) -> None:
        def worker() -> None:
            try:
                result = request_func()
                Clock.schedule_once(lambda _: on_success(result), 0)
                return
            except requests.HTTPError as ex:
                response = ex.response
                statusCode = response.status_code if response is not None else None
                payload = self._safe_extract_response_payload(response=response)
                Clock.schedule_once(lambda _: on_error(statusCode, payload), 0)
                return
            except Exception as ex:
                Clock.schedule_once(lambda _: on_error(None, {"detail": str(ex)}), 0)

        threading.Thread(target=worker, daemon=True).start()
