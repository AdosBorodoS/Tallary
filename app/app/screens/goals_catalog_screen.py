from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.widgets.bottom_nav_mixin import BottomNavMixin
from app.services.api_client import ApiClient
from app.services.session_service import SessionService


class GoalsCatalogScreen(BottomNavMixin, Screen):
    titleText = StringProperty("Каталог целей")

    # UI state
    searchText = StringProperty("")
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    # tabs: all | popular | achievement
    activeTab = StringProperty("all")

    # RV data
    goalsData = ListProperty([])

    # selection (optional)
    selectedGoalId = NumericProperty(0)
    selectedGoalName = StringProperty("")

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._allGoals: list[dict[str, Any]] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_goals_catalog()

    # ---------- UI handlers ----------
    def set_tab(self, tabName: str) -> None:
        self.activeTab = tabName
        self._apply_filters()

    def on_search_button_click(self) -> None:
        query = ""
        if "searchInput" in self.ids:
            query = str(self.ids.searchInput.text or "").strip()
            self.searchText = query
        else:
            query = str(self.searchText or "").strip()

        print(f"[GoalsCatalogScreen] search query='{query}'")
        self._apply_filters()

    def on_goal_open_button_click(self, goalId: int, goalName: str) -> None:
        self.selectedGoalId = int(goalId)
        self.selectedGoalName = str(goalName)
        print(f"[GoalsCatalogScreen] open goal id={self.selectedGoalId} name='{self.selectedGoalName}'")

        if not self.manager:
            return

        goalEditScreen = self.manager.get_screen("goal_edit")
        goalEditScreen.load_goal(self.selectedGoalId, self.selectedGoalName)
        self.manager.current = "goal_edit"


    def on_create_goal_button_click(self) -> None:
        print("[GoalsCatalogScreen] create goal click")
        # TODO позже: переход на экран создания цели
        self.manager.current = "goal_create"

    def on_search_icon_click(self) -> None:
        # Просто фокус в поле поиска
        if "searchInput" in self.ids:
            self.ids.searchInput.focus = True

    # ---------- data loading (placeholder now) ----------
    def _load_goals_catalog(self) -> None:
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Загрузка..."
        self.goalsData = []

        # Пока заглушка: имитируем ответ API
        Clock.schedule_once(lambda _: self._apply_goals_payload(self._fetch_goals_placeholder()), 0)

    def _fetch_goals_placeholder(self) -> list[dict[str, Any]]:
        return [
            {"id": 1, "goalName": "На машину"},
            {"id": 2, "goalName": "На отдых"},
            {"id": 3, "goalName": "На обучение"},
        ]

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
            goalId = item.get("id")
            goalName = item.get("goalName")
            if goalId is None or not goalName:
                continue
            normalized.append({"id": int(goalId), "goalName": str(goalName)})

        self._allGoals = normalized
        self.statusText = "" if len(self._allGoals) > 0 else "Целей пока нет"
        self._apply_filters()

    def _apply_filters(self) -> None:
        tab = (self.activeTab or "all").strip().lower()
        query = (self.searchText or "").strip().lower()

        goals = list(self._allGoals)

        # Заглушки логики табов (позже заменишь на реальные поля/сортировки)
        if tab == "popular":
            # допустим "популярные" — первые N
            goals = goals[:10]
        elif tab == "achievement":
            # допустим "по достижению" — просто другая сортировка по имени
            goals = sorted(goals, key=lambda x: x.get("goalName", ""))

        if query:
            goals = [g for g in goals if query in str(g.get("goalName") or "").lower()]

        self.goalsData = self._build_rv_data(goals)

    def _build_rv_data(self, goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for item in goals:
            goalId = int(item.get("id") or 0)
            goalName = str(item.get("goalName") or "").strip()
            if goalId <= 0 or not goalName:
                continue

            # Остальное — заглушки под будущий API (progress/participants/desc)
            data.append(
                {
                    "screen": self,
                    "goalId": goalId,
                    "goalName": goalName,
                    "goalDesc": "Описание цели будет подгружаться из API",
                    "progressText": "Прогресс: —",
                    "participantsText": "Участники: —",
                }
            )
        return data
