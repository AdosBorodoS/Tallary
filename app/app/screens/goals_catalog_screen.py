from __future__ import annotations

import threading
from typing import Any, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.widgets.bottom_nav_mixin import BottomNavMixin
from app.services.api_client import ApiClient
from app.services.schema import GetGoalTransactionsQuery
from app.services.session_service import SessionService


class GoalsCatalogScreen(BottomNavMixin, Screen):
    titleText = StringProperty("Каталог целей")

    searchText = StringProperty("")
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    activeTab = StringProperty("all")

    goalsData = ListProperty([])

    selectedGoalId = NumericProperty(0)
    selectedGoalName = StringProperty("")

    activeSort = StringProperty("operations")

    operationsAscending = BooleanProperty(False)
    achievementAscending = BooleanProperty(False)

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._allGoals: list[dict[str, Any]] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_goals_catalog()

    def toggle_sort(self, sortName: str) -> None:
        sortValue = (sortName or "").strip().lower()
        if sortValue not in ("operations", "achievement"):
            return

        if self.activeSort == sortValue:
            if sortValue == "operations":
                self.operationsAscending = not self.operationsAscending
            else:
                self.achievementAscending = not self.achievementAscending
        else:
            self.activeSort = sortValue
            if sortValue == "operations":
                self.operationsAscending = False
            else:
                self.achievementAscending = False

        self._apply_filters()


    def on_search_button_click(self) -> None:
        query = ""
        if "searchInput" in self.ids:
            query = str(self.ids.searchInput.text or "").strip()
            self.searchText = query
        else:
            query = str(self.searchText or "").strip()

        self._apply_filters()

    def on_goal_open_button_click(self, goalId: int, goalName: str) -> None:
        self.selectedGoalId = int(goalId)
        self.selectedGoalName = str(goalName)

        if not self.manager:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password
        selectedGoalId = int(self.selectedGoalId)

        goalMetaFromCatalog: dict[str, Any] = {}
        try:
            for item in list(self.goalsData or []):
                if not isinstance(item, dict):
                    continue
                if int(item.get("goalId") or 0) == selectedGoalId:
                    meta = item.get("goalMeta")
                    if isinstance(meta, dict):
                        goalMetaFromCatalog = dict(meta)
                    break
        except Exception:
            goalMetaFromCatalog = {}

        def request_func() -> dict[str, Any]:
            query = GetGoalTransactionsQuery(goalID=selectedGoalId)
            payload = self._apiClient.get_goal_transactions(userName, password, query)

            transactions: list[dict[str, Any]] = []
            metadata: dict[str, Any] = {}

            if isinstance(payload, dict):
                if isinstance(payload.get("transactions"), list):
                    transactions = [x for x in payload["transactions"] if isinstance(x, dict)]
                if isinstance(payload.get("metadata"), dict):
                    metadata = payload["metadata"]

            mergedMeta = dict(goalMetaFromCatalog)
            mergedMeta["transactions"] = transactions
            mergedMeta["metadata"] = metadata

            return mergedMeta

        def on_success(mergedMeta: dict[str, Any]) -> None:
            goalEditScreen = self.manager.get_screen("goal_edit")
            goalEditScreen.load_goal(selectedGoalId, self.selectedGoalName, mergedMeta)
            self.manager.current = "goal_edit"

        def on_error(statusCode: Optional[int], errorPayload: Any) -> None:
            goalEditScreen = self.manager.get_screen("goal_edit")
            goalEditScreen.load_goal(selectedGoalId, self.selectedGoalName, goalMetaFromCatalog)
            self.manager.current = "goal_edit"

        self._run_request_in_thread(
            request_func=request_func,
            on_success=on_success,
            on_error=on_error,
        )

    def on_create_goal_button_click(self) -> None:
        if self.manager:
            self.manager.current = "goal_create"

    def on_search_icon_click(self) -> None:
        if "searchInput" in self.ids:
            self.ids.searchInput.focus = True

    def _load_goals_catalog(self) -> None:
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            self._allGoals = []
            self.goalsData = []
            return

        self.isLoading = True
        self.statusText = "Загрузка..."
        self.goalsData = []

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        def request_func() -> list[dict[str, Any]]:
            goalsPayload = self._apiClient.get_goal(userName, password)
            goalsList = self._extract_goals_list(goalsPayload)

            enriched: list[dict[str, Any]] = []
            for goalItem in goalsList:
                goalId = self._safe_int(goalItem.get("id"))
                goalName = str(goalItem.get("goalName") or "").strip()
                if goalId <= 0 or not goalName:
                    continue

                meta = self._fetch_goal_metadata(userName, password, goalId)

                enriched.append(
                    {
                        "id": goalId,
                        "goalName": goalName,
                        "completionPercent": int(meta.get("completionPercent") or 0),
                        "operationsCount": int(meta.get("operationsCount") or 0),
                        "contributorsCount": int(meta.get("contributorsCount") or 0),
                        "currentValue": float(meta.get("currentValue") or 0.0),
                        "completionRatio": float(meta.get("completionRatio") or 0.0),
                        "contributorsTotal": float(meta.get("contributorsTotal") or 0.0),
                        "contributorsBreakdown": meta.get("contributorsBreakdown") or [],
                        "ruleScores": meta.get("ruleScores") or [],
                    }
                )

            return enriched

        self._run_request_in_thread(
            request_func=request_func,
            on_success=self._apply_goals_payload,
            on_error=self._on_load_error,
        )

    def _fetch_goal_metadata(self, userName: str, password: str, goalId: int) -> dict[str, Any]:
        try:
            query = GetGoalTransactionsQuery(goalID=goalId)
            payload = self._apiClient.get_goal_transactions(userName, password, query)
        except Exception:
            payload = None

        if not isinstance(payload, dict):
            return {
                "currentValue": 0,
                "completionRatio": 0,
                "completionPercent": 0,
                "operationsCount": 0,
                "contributorsTotal": 0,
                "contributorsCount": 0,
                "contributorsBreakdown": [],
                "ruleScores": [],
            }

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        contributorsBreakdown = metadata.get("contributorsBreakdown")
        contributorsCount = 0
        if isinstance(contributorsBreakdown, list):
            contributorsCount = len([x for x in contributorsBreakdown if isinstance(x, dict)])

        return {
            "currentValue": metadata.get("currentValue", 0),
            "completionRatio": metadata.get("completionRatio", 0),
            "completionPercent": metadata.get("completionPercent", 0),
            "operationsCount": metadata.get("operationsCount", 0),
            "contributorsTotal": metadata.get("contributorsTotal", 0),
            "contributorsCount": contributorsCount,
            "contributorsBreakdown": contributorsBreakdown if isinstance(contributorsBreakdown, list) else [],
            "ruleScores": metadata.get("ruleScores") if isinstance(metadata.get("ruleScores"), list) else [],
        }

    def _apply_goals_payload(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, list):
            self.statusText = "Некорректный ответ"
            self._allGoals = []
            self.goalsData = []
            return

        normalized: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue

            goalId = self._safe_int(item.get("id"))
            goalName = str(item.get("goalName") or "").strip()
            if goalId <= 0 or not goalName:
                continue

            normalized.append(item)

        self._allGoals = normalized
        self.statusText = "" if len(self._allGoals) > 0 else "Целей пока нет"
        self._apply_filters()

    def _apply_filters(self) -> None:
        sortMode = (self.activeSort or "operations").strip().lower()
        query = (self.searchText or "").strip().lower()

        goals = list(self._allGoals)

        if sortMode == "operations":
            ascending = bool(self.operationsAscending)
            goals = sorted(
                goals,
                key=lambda x: int(x.get("operationsCount") or 0),
                reverse=not ascending,
            )
        elif sortMode == "achievement":
            ascending = bool(self.achievementAscending)
            goals = sorted(
                goals,
                key=lambda x: float(x.get("completionRatio") or 0.0),
                reverse=not ascending,
            )

        if query:
            goals = [g for g in goals if query in str(g.get("goalName") or "").lower()]

        self.goalsData = self._build_rv_data(goals)

    def _build_rv_data(self, goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for item in goals:
            goalId = self._safe_int(item.get("id"))
            goalName = str(item.get("goalName") or "").strip()
            if goalId <= 0 or not goalName:
                continue

            completionPercent = int(item.get("completionPercent") or 0)
            operationsCount = int(item.get("operationsCount") or 0)
            contributorsCount = int(item.get("contributorsCount") or 0)

            completionRatio = float(item.get("completionRatio") or 0.0)

            data.append(
                {
                    "screen": self,
                    "goalId": goalId,
                    "goalName": goalName,
                    "progressText": f"Прогресс: {completionPercent}%",
                    "participantsText": f"Операции: {operationsCount} • Участники: {contributorsCount}",
                    "completionRatio": completionRatio,
                    "goalMeta": {
                        "id": goalId,
                        "goalName": goalName,
                        "currentValue": item.get("currentValue"),
                        "completionRatio": completionRatio,
                        "completionPercent": completionPercent,
                        "operationsCount": operationsCount,
                        "contributorsTotal": item.get("contributorsTotal"),
                        "contributorsBreakdown": item.get("contributorsBreakdown"),
                        "ruleScores": item.get("ruleScores"),
                    },
                }
            )
        return data

    @staticmethod
    def _extract_goals_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            return [x for x in payload["data"] if isinstance(x, dict)]
        return []

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
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

    def _on_load_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки целей: {detail}" if detail else "Ошибка загрузки целей"
        self._allGoals = []
        self.goalsData = []
