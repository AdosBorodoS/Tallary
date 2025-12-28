from __future__ import annotations

import json
import threading
from typing import Any, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.widgets.bottom_nav_mixin import BottomNavMixin
from app.services.api_client import ApiClient
from app.services.schema import (
    AddGoalPayload,
    GoalOperator,
    GaolParticipant,
    ParticipantCatalog,
)


class GoalCreateScreen(BottomNavMixin, Screen):
    titleText = StringProperty("Новая финансовая цель")

    goalNameText = StringProperty("")

    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    conditionsData = ListProperty([])
    participantsData = ListProperty([])

    friendSearchText = StringProperty("")
    friendSearchData = ListProperty([])
    selectedSearchFriendId = NumericProperty(0)
    selectedSearchFriendName = StringProperty("")

    friendSearchPopup = ObjectProperty(None, allownone=True)

    _conditions: list[dict[str, Any]] = []
    _participants: list[dict[str, Any]] = []
    _allFriends: list[dict[str, Any]] = []

    def __init__(self, apiClient: ApiClient, sessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService
        self._reset_form()

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_friends()
        self._refresh_lists()

    def on_back_button_click(self) -> None:
        self.on_nav_click("goals")

    def on_add_condition_button_click(self) -> None:
        self._conditions.append({"metric": "Баланс", "operator": ">=", "value": ""})
        self._refresh_lists()

    def on_delete_condition_click(self, index: int) -> None:
        if 0 <= index < len(self._conditions):
            self._conditions.pop(index)
        self._refresh_lists()

    def on_condition_metric_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self._conditions):
            self._conditions[index]["metric"] = str(value or "")

    def on_condition_operator_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self._conditions):
            self._conditions[index]["operator"] = str(value or "")

    def on_condition_value_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self._conditions):
            self._conditions[index]["value"] = str(value or "")

    def on_open_friend_search_popup_click(self) -> None:
        self.friendSearchText = ""
        self.selectedSearchFriendId = 0
        self.selectedSearchFriendName = ""
        self._apply_friend_search()

        if "friendSearchPopup" in self.ids:
            self.ids.friendSearchPopup.open()

    def on_friend_search_button_click(self) -> None:
        query = ""
        if "friendSearchInput" in self.ids:
            query = str(self.ids.friendSearchInput.text or "").strip()
        else:
            query = str(self.friendSearchText or "").strip()

        self.friendSearchText = query
        self._apply_friend_search()

    def on_friend_pick_click(self, friendId: int, friendName: str) -> None:
        self.selectedSearchFriendId = int(friendId)
        self.selectedSearchFriendName = str(friendName or "")
        self._apply_friend_search()

    def on_confirm_add_friend_to_goal_click(self) -> None:
        if self.selectedSearchFriendId <= 0:
            self.statusText = "Выбери друга из списка"
            return

        friendId = int(self.selectedSearchFriendId)
        friendName = str(self.selectedSearchFriendName)

        if any(int(p.get("id", 0)) == friendId for p in self._participants):
            pass
        else:
            self._participants.append({"id": friendId, "userName": friendName})

        self._refresh_lists()

        if self.friendSearchPopup:
            self.friendSearchPopup.dismiss()
            self.friendSearchPopup = None

        self.selectedSearchFriendId = 0
        self.selectedSearchFriendName = ""

    def on_remove_participant_click(self, participantId: int) -> None:
        self._participants = [p for p in self._participants if int(p.get("id", 0)) != int(participantId)]
        self._refresh_lists()

    def on_save_goal_button_click(self) -> None:
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        goalName = (self.goalNameText or "").strip()
        if not goalName:
            self.statusText = "Введите название цели"
            return

        if not self._conditions:
            self.statusText = "Добавьте хотя бы одно условие"
            return

        operators = self._build_operators_from_conditions()
        if not operators:
            self.statusText = "Некорректный оператор в условиях"
            return

        if all(int(op.goalRule or 0) == 0 for op in operators):
            self.statusText = "Укажите значение условия больше 0"
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        self.isLoading = True
        self.statusText = "Сохранение..."

        def request_func() -> dict:
            addGoalPayload = AddGoalPayload(goalName=goalName, operators=operators)
            createResp = self._apiClient.post_goal(userName, password, addGoalPayload)

            createdGoalId = self._extract_created_goal_id(createResp)

            if createdGoalId > 0:
                participantIds = self._collect_participants_ids()
                if participantIds:
                    participantsPayload = GaolParticipant(
                        goalID=createdGoalId,
                        participants=[ParticipantCatalog(userID=pid) for pid in participantIds],
                    )
                    self._apiClient.post_goal_participant(userName, password, participantsPayload)

            return {"createdGoalId": createdGoalId, "raw": createResp}

        def on_success(result: Any) -> None:
            self.isLoading = False

            createdGoalId = 0
            if isinstance(result, dict):
                createdGoalId = int(result.get("createdGoalId") or 0)

            self.statusText = "Цель создана"
            self._reset_form()

            self.on_nav_click("goals")

        def on_error(statusCode: Optional[int], errorPayload: Any) -> None:
            self.isLoading = False

            detail = ""
            if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
                detail = errorPayload["detail"].strip()

            self.statusText = f"Ошибка: {detail}" if detail else "Ошибка сохранения"

        self._run_request_in_thread(
            request_func=request_func,
            on_success=on_success,
            on_error=on_error,
        )

    def _build_operators_from_conditions(self) -> list[GoalOperator]:
        operatorMap = {
            "=": "==",
        }

        allowedOperators = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<="}

        operators: list[GoalOperator] = []
        for item in (self._conditions or []):
            opRaw = str(item.get("operator") or "").strip()
            op = operatorMap.get(opRaw, opRaw)

            valueRaw = str(item.get("value") or "").strip()
            goalRule = self._safe_int(valueRaw)

            if op not in allowedOperators:
                continue

            operators.append(GoalOperator(goalOperator=op, goalRule=goalRule))

        return operators


    def _collect_participants_ids(self) -> list[int]:
        participantIds: list[int] = []

        for p in (self._participants or []):
            pid = int(p.get("id") or 0)
            if pid > 0 and pid not in participantIds:
                participantIds.append(pid)

        return participantIds

    @staticmethod
    def _extract_created_goal_id(createResp: Any) -> int:

        if isinstance(createResp, dict):
            for key in ("id", "goalID", "goalId", "goal_id"):
                if key in createResp:
                    try:
                        return int(createResp.get(key) or 0)
                    except Exception:
                        pass

            data = createResp.get("data")
            if isinstance(data, dict):
                for key in ("id", "goalID", "goalId", "goal_id"):
                    if key in data:
                        try:
                            return int(data.get(key) or 0)
                        except Exception:
                            pass

        return 0

    def _load_friends(self) -> None:
        if not self._sessionService.is_authorized():
            self._allFriends = []
            self.friendSearchData = []
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        def request_func() -> Any:
            return self._apiClient.get_friends(userName, password)

        def on_success(payload: Any) -> None:
            self._allFriends = self._extract_friends_list(payload)
            self._apply_friend_search()

        def on_error(statusCode: Optional[int], errorPayload: Any) -> None:
            self._allFriends = []
            self._apply_friend_search()

        self._run_request_in_thread(
            request_func=request_func,
            on_success=on_success,
            on_error=on_error,
        )

    @staticmethod
    def _extract_friends_list(payload: Any) -> list[dict[str, Any]]:

        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]

        if isinstance(payload, dict):
            for key in ("data", "friends"):
                val = payload.get(key)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]

        return []

    def _reset_form(self) -> None:
        self.goalNameText = ""
        self.statusText = ""

        self._conditions = [
            {"metric": "Баланс", "operator": "=", "value": "0"},
        ]
        self._participants = []

        self.friendSearchText = ""
        self.selectedSearchFriendId = 0
        self.selectedSearchFriendName = ""

        self._refresh_lists()
        self._apply_friend_search()

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

    def _safe_int(self, value: str) -> int:
        try:
            return int(float(str(value).replace(",", ".").strip()))
        except Exception:
            return 0

    def _run_request_in_thread(
        self,
        request_func,
        on_success,
        on_error,
    ) -> None:
        def worker() -> None:
            try:
                result = request_func()
                Clock.schedule_once(lambda *_: on_success(result), 0)
            except requests.HTTPError as e:
                status_code = None
                payload = None
                try:
                    status_code = e.response.status_code if e.response is not None else None
                    payload = e.response.json() if e.response is not None else None
                except Exception:
                    payload = None
                Clock.schedule_once(lambda *_: on_error(status_code, payload), 0)
            except Exception as e:
                Clock.schedule_once(lambda *_: on_error(None, {"detail": str(e)}), 0)

        threading.Thread(target=worker, daemon=True).start()
