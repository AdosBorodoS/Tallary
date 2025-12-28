from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.widgets.bottom_nav_mixin import BottomNavMixin


class HomeScreen(BottomNavMixin, Screen):
    monthTitleText = StringProperty("Июнь")
    headerTitleText = StringProperty("Обзор за Июнь")

    expenseText = StringProperty("— ₽")
    incomeText = StringProperty("— ₽")
    balanceText = StringProperty("— ₽")

    donutTitleText = StringProperty("Всего расходов")
    donutValueText = StringProperty("— ₽")

    statusText = StringProperty("")
    isLoading = BooleanProperty(False)
    isExpenseTab = BooleanProperty(True)

    totalExpense = NumericProperty(0)
    totalIncome = NumericProperty(0)

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService
        self._expenseCategories: list[dict] = []
        self._incomeCategories: list[dict] = []
        
    def _is_user_valid(self) -> None:
        if not self._sessionService.is_authorized():
            self.on_nav_click("login")
            return

    def on_kv_post(self, base_widget) -> None:
        self._set_empty_chart()

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_home_data()

    def on_logout_button_click(self) -> None:
        print("[HomeScreen] logout click")
        self._sessionService.clear()
        self.on_nav_click("login")

    def set_expense_tab(self) -> None:
        self.isExpenseTab = True
        self.donutTitleText = "Всего расходов"
        self.donutValueText = self.expenseText

        if self._expenseCategories:
            self._render_categories_chart(self._expenseCategories)
        else:
            self._set_empty_chart()


    def set_income_tab(self) -> None:
        self.isExpenseTab = False
        self.donutTitleText = "Всего доходов"
        self.donutValueText = self.incomeText

        if self._incomeCategories:
            self._render_categories_chart(self._incomeCategories)
        else:
            self._set_empty_chart()

    def on_view_analytics_button_click(self) -> None:
        self.on_nav_click("analytics")

    def on_transactions_button_click(self) -> None:
        self.on_nav_click("transactions")

    def on_friends_button_click(self) -> None:
        self.on_nav_click("friends")

    def on_goals_button_click(self) -> None:
        self.on_nav_click("goals")

    def _load_home_data(self) -> None:
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Загрузка..."
        self._set_placeholders()
        self._set_empty_chart()

        self._run_request_in_thread(
            request_func=self._fetch_home_payload,
            on_success=self._apply_home_payload,
            on_error=self._handle_home_error,
        )

    def _fetch_home_payload(self) -> dict:
        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        expenseDistribution = self._apiClient.get_analytics_expense_category_distribution(
            userName, password
        )

        incomeDistribution = self._apiClient.get_analytics_income_category_distribution(
            userName, password
        )

        totalExpense = 0
        if isinstance(expenseDistribution, dict):
            meta = expenseDistribution.get("meta") or {}
            totalExpense = float(meta.get("totalExpense") or 0)

        totalIncome = 0
        if isinstance(incomeDistribution, dict):
            meta = incomeDistribution.get("meta") or {}
            totalIncome = float(meta.get("totalIncome") or 0)

        return {
            "categoriesExpense": expenseDistribution,
            "categoriesIncome": incomeDistribution,
            "totals": {
                "expense": totalExpense,
                "income": totalIncome,
                "balance": totalIncome - totalExpense,
            },
            "period": {"monthTitle": self.monthTitleText},
        }

    def _apply_home_payload(self, result: Any) -> None:
        self.isLoading = False

        if not isinstance(result, dict):
            self.statusText = "Некорректный ответ"
            self._set_placeholders()
            self._set_empty_chart()
            return

        self.headerTitleText = f"Общий обзор"

        totals = result.get("totals") or {}
        try:
            self.totalExpense = float(totals.get("expense") or 0)
        except Exception:
            self.totalExpense = 0

        try:
            self.totalIncome = float(totals.get("income") or 0)
        except Exception:
            self.totalIncome = 0

        self.expenseText = self._format_money(self.totalExpense)
        self.incomeText = self._format_money(self.totalIncome)
        self.balanceText = self._format_money(self.totalIncome - self.totalExpense)

        expensePayload = result.get("categoriesExpense") or {}
        incomePayload = result.get("categoriesIncome") or {}

        self._expenseCategories = expensePayload.get("data") if isinstance(expensePayload, dict) else []
        self._incomeCategories = incomePayload.get("data") if isinstance(incomePayload, dict) else []

        if not isinstance(self._expenseCategories, list):
            self._expenseCategories = []
        if not isinstance(self._incomeCategories, list):
            self._incomeCategories = []

        if self.isExpenseTab:
            self.donutTitleText = "Всего расходов"
            self.donutValueText = self.expenseText
            self._render_categories_chart(self._expenseCategories)
        else:
            self.donutTitleText = "Всего доходов"
            self.donutValueText = self.incomeText
            self._render_categories_chart(self._incomeCategories)

        self.statusText = ""

    def _handle_home_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False
        self._set_placeholders()
        self._set_empty_chart()

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки"

    def _set_empty_chart(self) -> None:
        chart = getattr(self.ids, "donutChart", None)
        if chart is None:
            if "donutChart" in self.ids:
                chart = self.ids["donutChart"]
        if chart is None:
            return
        chart.clear()

    def _render_categories_chart(self, categories: list[dict]) -> None:
        chart = self.ids.get("donutChart")
        if chart is None:
            return

        fractions: list[float] = []
        for item in categories:
            if not isinstance(item, dict):
                continue
            percent = item.get("percent")
            try:
                fractions.append(float(percent) / 100.0)
            except Exception:
                continue

        if len(fractions) == 0:
            chart.clear()
            return

        chart.set_slices(fractions)

    def _set_placeholders(self) -> None:
        self.expenseText = "— ₽"
        self.incomeText = "— ₽"
        self.balanceText = "— ₽"
        self.donutValueText = "— ₽"

    def _format_money(self, value: Any) -> str:
        if value is None:
            return "— ₽"
        try:
            intValue = int(value)
            return f"{intValue:,}".replace(",", " ") + " ₽"
        except Exception:
            return "— ₽"

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
