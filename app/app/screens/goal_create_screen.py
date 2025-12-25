from __future__ import annotations

from typing import Any

from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from app.widgets.bottom_nav_mixin import BottomNavMixin
from app.services.api_client import ApiClient
from app.services.session_service import SessionService


class GoalCreateScreen(BottomNavMixin, Screen):
    titleText = StringProperty("Новая финансовая цель")

    # form fields
    goalNameText = StringProperty("")

    # state
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    # lists on main screen
    conditionsData = ListProperty([])
    participantsData = ListProperty([])

    # friend search popup state
    friendSearchText = StringProperty("")
    friendSearchData = ListProperty([])
    selectedSearchFriendId = NumericProperty(0)
    selectedSearchFriendName = StringProperty("")

    friendSearchPopup = ObjectProperty(None, allownone=True)

    # internal
    _conditions: list[dict[str, Any]] = []
    _participants: list[dict[str, Any]] = []
    _allFriends: list[dict[str, Any]] = []

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._reset_form()

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_friends_placeholder()
        self._refresh_lists()

    # ---------- navigation ----------
    def on_back_button_click(self) -> None:
        print("[GoalCreateScreen] back click")
        self.on_nav_click("goals")

    # ---------- conditions ----------
    def on_add_condition_button_click(self) -> None:
        print("[GoalCreateScreen] add condition click")
        self._conditions.append({"metric": "Баланс", "operator": ">=", "value": ""})
        self._refresh_lists()

    def on_delete_condition_click(self, index: int) -> None:
        print(f"[GoalCreateScreen] delete condition index={index}")
        if 0 <= index < len(self._conditions):
            self._conditions.pop(index)
        self._refresh_lists()

    def on_condition_metric_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self._conditions):
            self._conditions[index]["metric"] = str(value or "")
        print(f"[GoalCreateScreen] condition[{index}] metric='{value}'")

    def on_condition_operator_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self._conditions):
            self._conditions[index]["operator"] = str(value or "")
        print(f"[GoalCreateScreen] condition[{index}] operator='{value}'")

    def on_condition_value_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self._conditions):
            self._conditions[index]["value"] = str(value or "")

    # ---------- participants (popup search) ----------
    def on_open_friend_search_popup_click(self) -> None:
        print("[GoalCreateScreen] open friend search popup")

        self.friendSearchText = ""
        self.selectedSearchFriendId = 0
        self.selectedSearchFriendName = ""
        self._apply_friend_search()

        # Popup class defined in KV as FriendSearchPopup@Popup
        popup = Popup(title="", size_hint=(0.92, 0.62), auto_dismiss=True)
        popup.content = self._build_friend_popup_content()
        self.friendSearchPopup = popup
        popup.open()

    def _build_friend_popup_content(self):
        # Content is created from kv rule via Factory, but we avoid Factory import here:
        # We will build it using ids in kv by using "FriendSearchPopupContent" rule
        # If your project uses Builder rules, easiest: create widget class in KV.
        # Here we assume KV defines <FriendSearchPopupContent@BoxLayout>.
        from kivy.factory import Factory

        content = Factory.FriendSearchPopupContent()
        content.screen = self
        return content

    def on_friend_search_button_click(self) -> None:
        query = ""
        if "friendSearchInput" in self.ids:
            # если вдруг используешь ids экрана — не обяз.
            query = str(self.ids.friendSearchInput.text or "").strip()
        else:
            query = str(self.friendSearchText or "").strip()

        self.friendSearchText = query
        print(f"[GoalCreateScreen] friend search query='{query}'")
        self._apply_friend_search()

    def on_friend_pick_click(self, friendId: int, friendName: str) -> None:
        self.selectedSearchFriendId = int(friendId)
        self.selectedSearchFriendName = str(friendName or "")
        print(f"[GoalCreateScreen] picked friend id={self.selectedSearchFriendId} name='{self.selectedSearchFriendName}'")
        self._apply_friend_search()  # чтобы подсветка обновилась

    def on_confirm_add_friend_to_goal_click(self) -> None:
        if self.selectedSearchFriendId <= 0:
            self.statusText = "Выбери друга из списка"
            print("[GoalCreateScreen] add friend -> no selection")
            return

        friendId = int(self.selectedSearchFriendId)
        friendName = str(self.selectedSearchFriendName)

        # не добавляем дубликаты
        if any(int(p.get("id", 0)) == friendId for p in self._participants):
            print(f"[GoalCreateScreen] add friend -> already exists id={friendId}")
        else:
            self._participants.append({"id": friendId, "userName": friendName})
            print(f"[GoalCreateScreen] add friend to participants id={friendId} name='{friendName}'")

        self._refresh_lists()

        if self.friendSearchPopup:
            self.friendSearchPopup.dismiss()
            self.friendSearchPopup = None

        # очистим выбор после добавления
        self.selectedSearchFriendId = 0
        self.selectedSearchFriendName = ""

    def on_remove_participant_click(self, participantId: int) -> None:
        print(f"[GoalCreateScreen] remove participant id={participantId}")
        self._participants = [p for p in self._participants if int(p.get("id", 0)) != int(participantId)]
        self._refresh_lists()

    # ---------- save ----------
    def on_save_goal_button_click(self) -> None:
        goalName = (self.goalNameText or "").strip()
        if not goalName:
            self.statusText = "Введите название цели"
            return

        payload = self._build_goal_payload(goalName)

        # ВЫВОД В КОНСОЛЬ (как ты просил)
        print("[GoalCreateScreen] SAVE PAYLOAD:")
        print(payload)

        self.statusText = "Цель сохранена (заглушка)"

    def _build_goal_payload(self, goalName: str) -> dict[str, Any]:
        operators: list[dict[str, Any]] = []

        for item in self._conditions:
            op = str(item.get("operator") or "").strip()
            valueRaw = str(item.get("value") or "").strip()

            if not op:
                continue

            goalRule = self._safe_int(valueRaw)
            operators.append({"goalOperator": op, "goalRule": goalRule})

        currentUserId = self._get_current_user_id()

        participantsIds: list[int] = []
        if currentUserId > 0:
            participantsIds.append(currentUserId)

        for p in self._participants:
            pid = int(p.get("id") or 0)
            if pid > 0 and pid not in participantsIds:
                participantsIds.append(pid)

        participants = [{"userID": pid} for pid in participantsIds]

        return {
            "goalName": goalName,
            "operators": operators,
            "participants": participants,
        }

    # ---------- helpers ----------
    def _reset_form(self) -> None:
        self.goalNameText = ""
        self.statusText = ""

        self._conditions = [
            {"metric": "Баланс", "operator": ">", "value": "20000"},
            {"metric": "Баланс", "operator": "<", "value": "200000"},
        ]
        self._participants = []

        self.friendSearchText = ""
        self.selectedSearchFriendId = 0
        self.selectedSearchFriendName = ""

        self._refresh_lists()

    def _refresh_lists(self) -> None:
        self.conditionsData = self._build_conditions_rv_data(self._conditions)
        self.participantsData = self._build_participants_rv_data(self._participants)

    def _build_conditions_rv_data(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for idx, item in enumerate(items):
            data.append(
                {
                    "screen": self,
                    "index": idx,
                    "metricValue": str(item.get("metric") or "Баланс"),
                    "operatorValue": str(item.get("operator") or ">"),
                    "valueText": str(item.get("value") or ""),
                }
            )
        return data

    def _build_participants_rv_data(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for item in items:
            participantId = int(item.get("id") or 0)
            userName = str(item.get("userName") or "").strip()
            if participantId <= 0 or not userName:
                continue
            data.append({"screen": self, "participantId": participantId, "userName": userName})
        return data

    def _load_friends_placeholder(self) -> None:
        # Заглушка "друзей" как будто из API /friends:
        self._allFriends = [
            {"id": 2, "userName": "user1"},
            {"id": 3, "userName": "alex"},
            {"id": 4, "userName": "marina"},
            {"id": 5, "userName": "sergey"},
        ]
        self._apply_friend_search()

    def _apply_friend_search(self) -> None:
        query = (self.friendSearchText or "").strip().lower()

        friends = list(self._allFriends)
        if query:
            friends = [f for f in friends if query in str(f.get("userName") or "").lower()]

        rvData: list[dict[str, Any]] = []
        for f in friends:
            fid = int(f.get("id") or 0)
            name = str(f.get("userName") or "").strip()
            if fid <= 0 or not name:
                continue
            rvData.append(
                {
                    "screen": self,
                    "friendId": fid,
                    "friendName": name,
                    "isSelected": True if self.selectedSearchFriendId == fid else False,
                }
            )

        self.friendSearchData = rvData

    def _get_current_user_id(self) -> int:
        # Подстройка под твой SessionService (не знаю точное API)
        # Популярные варианты:
        # - self._sessionService.userId
        # - self._sessionService.userID
        # - self._sessionService.get_user_id()
        if hasattr(self._sessionService, "get_user_id"):
            try:
                val = self._sessionService.get_user_id()
                return int(val or 0)
            except Exception:
                return 0

        for attr in ("userId", "userID", "currentUserId", "currentUserID"):
            if hasattr(self._sessionService, attr):
                try:
                    return int(getattr(self._sessionService, attr) or 0)
                except Exception:
                    return 0

        return 0

    def _safe_int(self, value: str) -> int:
        try:
            return int(float(value))
        except Exception:
            return 0
