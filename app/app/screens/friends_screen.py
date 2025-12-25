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
from app.services.schema import GetUsersQuery, PostFriendPayload, DeleteFriendPayload

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

    def on_refresh_button_click(self) -> None:
        self._load_lists(force=True)

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_lists()

    def on_back_button_click(self) -> None:
        self.on_nav_click("home")

    def on_search_button_click(self) -> None:
        query = (self.searchText or "").strip()
        print(f"[FriendsScreen] search query='{query}'")
        self._apply_users_search()

    def on_friend_row_click(self, userId: int, userName: str) -> None:
        self.selectedFriendId = int(userId)
        self.selectedFriendName = str(userName)

    def on_user_row_click(self, userId: int, userName: str) -> None:
        self.selectedUserId = int(userId)
        self.selectedUserName = str(userName)

    def on_add_friend_button_click(self) -> None:
        if self.selectedUserId <= 0:
            self.statusText = "Сначала выбери пользователя из списка ниже"
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password
        payload = PostFriendPayload(friendID=int(self.selectedUserId))

        self.isLoading = True
        self.statusText = "Добавляю в друзья..."

        self._run_request_in_thread(
            request_func=lambda: self._apiClient.post_friends(userName, password, payload),
            on_success=lambda _res: self._load_lists(force=True),
            on_error=self._handle_error,
        )

    def on_goals_button_click(self) -> None:
        self.on_nav_click("goals")

    def _load_lists(self, force: bool = False) -> None:
        if self.isLoading and not force:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            self.friendsData = []
            self.usersData = []
            return

        self.isLoading = True
        self.statusText = "Загрузка..."
        self.friendsData = []
        self.usersData = []
        self.selectedUserId = 0
        self.selectedUserName = ""
        self.selectedFriendId = 0
        self.selectedFriendName = ""
        self.usersEmptyText = ""

        self._run_request_in_thread(
            request_func=self._fetch_payload_from_api,
            on_success=self._apply_payload,
            on_error=self._handle_error,
        )

    def _fetch_payload_from_api(self) -> dict:
        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        friends = self._apiClient.get_friends(userName, password)
        users = self._apiClient.get_users(userName, password, GetUsersQuery())

        return {"friends": friends, "users": users}

    def _apply_payload(self, result: Any) -> None:
        self.isLoading = False

        if not isinstance(result, dict):
            self.statusText = "Некорректный ответ"
            return

        friendsRaw = result.get("friends")
        usersRaw = result.get("users")

        self._allFriends = self._normalize_people_list(raw=friendsRaw, listKey=None)
        allUsers = self._normalize_people_list(raw=usersRaw, listKey="data")

        currentUserName = str(self._sessionService.get_user_name() or "").strip()
        selfId: int | None = None
        for u in allUsers:
            if str(u.get("userName")) == currentUserName:
                try:
                    selfId = int(u.get("id"))
                except Exception:
                    selfId = None
                break

        friendIds = set()
        for f in self._allFriends:
            try:
                friendIds.add(int(f.get("id")))
            except Exception:
                continue

        filteredUsers: list[dict] = []
        for u in allUsers:
            try:
                uid = int(u.get("id"))
            except Exception:
                continue

            if selfId is not None and uid == selfId:
                continue
            if uid in friendIds:
                continue

            filteredUsers.append(u)

        self._allUsers = filteredUsers

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
            if personId is None:
                continue

            userNameValue = str(item.get("userName") or "").strip()
            if not userNameValue:
                userNameValue = f"User #{personId}"

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

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password
        payload = DeleteFriendPayload(friendID=int(self.selectedFriendId))

        self.isLoading = True
        self.statusText = "Удаляю друга..."

        self._run_request_in_thread(
            request_func=lambda: self._apiClient.delete_friends(userName, password, payload),
            on_success=lambda _res: self._load_lists(force=True),
            on_error=self._handle_error,
        )


    def _apply_users_search(self) -> None:
        query = (self.searchText or "").strip().lower()

        if not query:
            friendsFiltered = self._allFriends
        else:
            friendsFiltered = []
            for item in self._allFriends:
                if query in str(item.get("userName") or "").lower():
                    friendsFiltered.append(item)

        self.friendsData = self._build_rv_data(friendsFiltered, rowType="friend")

        if not query:
            usersFiltered = self._allUsers
        else:
            usersFiltered = []
            for item in self._allUsers:
                if query in str(item.get("userName") or "").lower():
                    usersFiltered.append(item)

        self.usersData = self._build_rv_data(usersFiltered, rowType="user")

        if query and len(usersFiltered) == 0:
            self.usersEmptyText = "Ничего не найдено"
        else:
            self.usersEmptyText = ""

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
