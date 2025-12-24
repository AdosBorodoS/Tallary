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
    # Header / period
    monthTitleText = StringProperty("Июнь")
    headerTitleText = StringProperty("Обзор за Июнь")

    # KPI
    expenseText = StringProperty("— ₽")
    incomeText = StringProperty("— ₽")
    balanceText = StringProperty("— ₽")

    # Center donut labels
    donutTitleText = StringProperty("Всего расходов")
    donutValueText = StringProperty("— ₽")

    # State
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)
    isExpenseTab = BooleanProperty(True)

    # Totals numeric (for later)
    totalExpense = NumericProperty(0)
    totalIncome = NumericProperty(0)

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        # на будущее: хранить последние данные категорий
        self._expenseCategories: list[dict] = []
        self._incomeCategories: list[dict] = []

    def on_kv_post(self, base_widget) -> None:
        # Приводим график в "пустое" состояние при старте
        self._set_empty_chart()

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_home_data()

    # -------- UI handlers --------
    def on_month_dropdown_click(self) -> None:
        # TODO: открыть выбор месяца/периода
        pass

    def set_expense_tab(self) -> None:
        self.isExpenseTab = True
        self.donutTitleText = "Всего расходов"
        self.donutValueText = self.expenseText
        # TODO: когда будут реальные данные:
        # self._render_categories_chart(self._expenseCategories)

        # Пока данных нет — пустой график
        self._set_empty_chart()

    def set_income_tab(self) -> None:
        self.isExpenseTab = False
        self.donutTitleText = "Всего доходов"
        self.donutValueText = self.incomeText
        # TODO: когда будут реальные данные:
        # self._render_categories_chart(self._incomeCategories)

        self._set_empty_chart()

    def on_view_analytics_button_click(self) -> None:
        self.on_nav_click("analytics")

    def on_transactions_button_click(self) -> None:
        self.on_nav_click("transactions")

    # -------- API scaffold --------
    def _load_home_data(self) -> None:
        """
        Здесь позже будут реальные запросы к API.
        Сейчас — заглушка: выставляем плейсхолдеры и пустой график.
        """
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Загрузка..."
        self._set_placeholders()
        self._set_empty_chart()

        # TODO: заменить на реальные запросы:
        # 1) summary totals (expense/income/balance)
        # 2) categories breakdown (expense or income)
        self._run_request_in_thread(
            request_func=self._fetch_home_payload_placeholder,
            on_success=self._apply_home_payload,
            on_error=self._handle_home_error,
        )

    def _fetch_home_payload_placeholder(self) -> dict:
        """
        Заглушка.
        Позже: дернуть ApiClient и вернуть объединённый payload.
        """
        return {
            "totals": {
                "expense": None,
                "income": None,
                "balance": None,
            },
            "categoriesExpense": {
                "status": "success",
                "data": [],
                "meta": {"totalExpense": 0},
            },
            "categoriesIncome": {
                "status": "success",
                "data": [],
                "meta": {"totalIncome": 0},
            },
            "period": {"monthTitle": "Июнь"},
        }

    def _apply_home_payload(self, result: Any) -> None:
        self.isLoading = False

        if not isinstance(result, dict):
            self.statusText = "Некорректный ответ"
            self._set_placeholders()
            self._set_empty_chart()
            return

        period = result.get("period") or {}
        monthTitle = str(period.get("monthTitle") or "Июнь")
        self.monthTitleText = monthTitle
        self.headerTitleText = f"Обзор за {monthTitle}"

        totals = result.get("totals") or {}
        self.expenseText = self._format_money(totals.get("expense"))
        self.incomeText = self._format_money(totals.get("income"))
        self.balanceText = self._format_money(totals.get("balance"))

        # Центр donut зависит от вкладки
        self.donutValueText = self.expenseText if self.isExpenseTab else self.incomeText

        # Заглушки категорий
        expensePayload = result.get("categoriesExpense") or {}
        incomePayload = result.get("categoriesIncome") or {}
        self._expenseCategories = (expensePayload.get("data") or []) if isinstance(expensePayload, dict) else []
        self._incomeCategories = (incomePayload.get("data") or []) if isinstance(incomePayload, dict) else []

        # Пока нет данных — пусто
        self._set_empty_chart()
        self.statusText = ""

    def _handle_home_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False
        self._set_placeholders()
        self._set_empty_chart()

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки"

    # -------- chart helpers --------
    def _set_empty_chart(self) -> None:
        chart = getattr(self.ids, "donutChart", None)
        if chart is None:
            # на случай если kv еще не применился
            if "donutChart" in self.ids:
                chart = self.ids["donutChart"]
        if chart is None:
            return
        chart.clear()

    def _render_categories_chart(self, categories: list[dict]) -> None:
        """
        categories пример (как у тебя из API):
        [{"category": "...", "amount": 110257, "percent": 96.02}, ...]
        """
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

    # -------- utils --------
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
