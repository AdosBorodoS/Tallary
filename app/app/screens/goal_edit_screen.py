from __future__ import annotations

import json
from typing import Any

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from app.widgets.bottom_nav_mixin import BottomNavMixin
from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from kivy.uix.popup import Popup
# from kivy.factory import Factory

class FriendPickPopupContent(BoxLayout):
    screen = ObjectProperty(None)

class GoalEditScreen(BottomNavMixin, Screen):
    # goal identity
    goalId = NumericProperty(0)

    # UI state
    titleText = StringProperty("Моя цель")
    goalNameText = StringProperty("")
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    # RV data
    conditionsData = ListProperty([])
    participantsData = ListProperty([])

    # friend popup
    friendSearchText = StringProperty("")
    friendsData = ListProperty([])
    selectedFriendId = NumericProperty(0)
    selectedFriendName = StringProperty("")

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._friendsPopup = None
        self._apiClient = apiClient
        self._sessionService = sessionService

        # локальные кэши
        self._friendsCache: list[dict[str, Any]] = []

    # ---------- navigation from catalog ----------
    def load_goal(self, goalId: int, goalName: str = "") -> None:
        self.goalId = int(goalId)
        self.goalNameText = str(goalName or "")
        self.titleText = f"Моя Цель: {self.goalNameText}" if self.goalNameText else "Моя цель"

        # Никаких popup.open() тут быть не должно
        Clock.schedule_once(lambda _: self._load_goal_placeholder(), 0)

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)

        # На всякий случай: если попап был открыт ранее — закрываем при входе на экран
        if "friendsPopup" in self.ids:
            try:
                self.ids.friendsPopup.dismiss()
            except Exception:
                pass

        # Если пришли с каталога и ещё не подгружали данные — грузим заглушки
        if self.goalId > 0 and not self.conditionsData:
            self._load_goal_placeholder()


    # ---------- placeholder loaders ----------
    def _load_goal_placeholder(self) -> None:
        if self.isLoading:
            return
        self.isLoading = True
        self.statusText = "Загрузка..."
        self.conditionsData = []
        self.participantsData = []

        Clock.schedule_once(lambda _: self._apply_goal_payload(self._fetch_goal_placeholder()), 0)

    def _fetch_goal_placeholder(self) -> dict[str, Any]:
        # TODO: заменить на API: GET /goals/{id}
        return {
            "id": self.goalId or 1,
            "goalName": self.goalNameText or "Автомобиль",
            "operators": [
                {"goalOperator": ">=", "goalRule": 500000},
                {"goalOperator": "<", "goalRule": 2000000},
            ],
            "participants": [
                {"userID": 2, "userName": "user1"},
            ],
        }

    def _apply_goal_payload(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, dict):
            self.statusText = "Некорректный ответ"
            return

        self.goalNameText = str(payload.get("goalName") or "")
        self.titleText = f"Моя Цель: {self.goalNameText}" if self.goalNameText else "Моя цель"
        self.statusText = ""

        operators = payload.get("operators") or []
        conditionsRv: list[dict[str, Any]] = []
        for i, item in enumerate(operators):
            if not isinstance(item, dict):
                continue
            conditionsRv.append(
                {
                    "screen": self,
                    "index": i,
                    "operatorValue": str(item.get("goalOperator") or ">="),
                    "valueText": str(item.get("goalRule") or ""),
                }
            )
        self.conditionsData = conditionsRv

        participants = payload.get("participants") or []
        participantsRv: list[dict[str, Any]] = []
        for item in participants:
            if not isinstance(item, dict):
                continue
            userId = int(item.get("userID") or 0)
            userName = str(item.get("userName") or "").strip()
            if userId <= 0:
                continue
            participantsRv.append({"screen": self, "participantId": userId, "userName": userName})
        self.participantsData = participantsRv

    # ---------- top bar ----------
    def on_back_button_click(self) -> None:
        print("[GoalEditScreen] back button click")

        if not self.manager:
            return

        # Правильное имя каталога целей
        if self.manager.has_screen("goals"):
            self.manager.current = "goals"
            return

        # Если вдруг поменяешь имя в будущем
        if self.manager.has_screen("goals_catalog"):
            self.manager.current = "goals_catalog"
            return

        # Фоллбек, чтобы не падало
        if self.manager.has_screen("home"):
            self.manager.current = "home"

    def on_save_button_click(self) -> None:
        payload = self._build_payload_placeholder()
        print("[GoalEditScreen] save click payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    def on_delete_button_click(self) -> None:
        print(f"[GoalEditScreen] delete click goalId={self.goalId} (placeholder)")

    # ---------- conditions ----------
    def on_add_condition_button_click(self) -> None:
        print("[GoalEditScreen] add condition click")
        nextIndex = len(self.conditionsData)
        self.conditionsData = list(self.conditionsData) + [
            {"screen": self, "index": nextIndex, "operatorValue": ">=", "valueText": ""}
        ]

    def on_delete_condition_click(self, index: int) -> None:
        print(f"[GoalEditScreen] delete condition index={index}")
        updated = [c for c in self.conditionsData if int(c.get("index") or -1) != int(index)]
        for i, item in enumerate(updated):
            item["index"] = i
            item["screen"] = self
        self.conditionsData = updated

    def on_condition_operator_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self.conditionsData):
            self.conditionsData[index]["operatorValue"] = value

    def on_condition_value_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self.conditionsData):
            self.conditionsData[index]["valueText"] = value

    # ---------- participants ----------
    def on_open_friend_popup_click(self) -> None:
        print("[GoalEditScreen] open friend popup click")

        self._load_friends_placeholder()
        self.selectedFriendId = 0
        self.selectedFriendName = ""

        if self._friendsPopup is None:
            popupContent = FriendPickPopupContent(screen=self)

            self._friendsPopup = Popup(
                title="",
                content=popupContent,
                auto_dismiss=True,
                size_hint=(0.92, 0.62),
                separator_height=0,
            )
        else:
            # на всякий случай обновляем ссылку на screen
            self._friendsPopup.content.screen = self

        self._friendsPopup.open()


    def close_friend_popup(self) -> None:
        if self._friendsPopup is not None:
            self._friendsPopup.dismiss()


    def _load_friends_placeholder(self) -> None:
        # TODO: заменить на API: GET /friends
        self._friendsCache = [
            {"id": 2, "userName": "user1"},
            {"id": 3, "userName": "user2"},
            {"id": 4, "userName": "user3"},
        ]
        self.friendsData = self._build_friend_rv_data(self._friendsCache)

    def _build_friend_rv_data(self, friends: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for item in friends:
            friendId = int(item.get("id") or 0)
            friendName = str(item.get("userName") or "").strip()
            if friendId <= 0 or not friendName:
                continue
            data.append(
                {
                    "screen": self,
                    "friendId": friendId,
                    "friendName": friendName,
                    "isSelected": friendId == self.selectedFriendId,
                }
            )
        return data

    def on_friend_pick_click(self, friendId: int, friendName: str) -> None:
        self.selectedFriendId = int(friendId)
        self.selectedFriendName = str(friendName)
        print(f"[GoalEditScreen] picked friend id={self.selectedFriendId} name='{self.selectedFriendName}'")
        self.friendsData = self._build_friend_rv_data(self._friendsCache)

    def on_confirm_add_friend_click(self) -> None:
        if self.selectedFriendId <= 0:
            return
        print(f"[GoalEditScreen] confirm add friend userID={self.selectedFriendId} (placeholder)")

        existingIds = {int(p.get("participantId") or 0) for p in self.participantsData}
        if self.selectedFriendId not in existingIds:
            self.participantsData = list(self.participantsData) + [
                {"screen": self, "participantId": self.selectedFriendId, "userName": self.selectedFriendName}
            ]

        if "friendsPopup" in self.ids:
            self.ids.friendsPopup.dismiss()

        self.close_friend_popup()

    def on_remove_participant_click(self, participantId: int) -> None:
        print(f"[GoalEditScreen] remove participant userID={participantId} (placeholder)")
        self.participantsData = [p for p in self.participantsData if int(p.get("participantId") or 0) != int(participantId)]

    # ---------- payload ----------
    def _build_payload_placeholder(self) -> dict[str, Any]:
        operators: list[dict[str, Any]] = []
        for item in self.conditionsData:
            goalOperator = str(item.get("operatorValue") or "").strip()
            rawValue = str(item.get("valueText") or "").strip()
            try:
                goalRule = int(float(rawValue.replace(",", "."))) if rawValue else 0
            except Exception:
                goalRule = 0
            operators.append({"goalOperator": goalOperator, "goalRule": goalRule})

        return {
            "goalId": int(self.goalId),
            "goalName": str(self.goalNameText or ""),
            "operators": operators,
            "participants": [{"userID": int(p.get("participantId") or 0)} for p in self.participantsData if int(p.get("participantId") or 0) > 0],
        }
