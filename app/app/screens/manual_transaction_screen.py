from __future__ import annotations

import threading
from typing import Any, Optional

import requests
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.schema import PostBankTransactionsManualLoadPayload, PostBankTransactionsQuery
from app.services.session_service import SessionService


class ManualTransactionScreen(Screen):
    # dropdown values (пока заглушки)
    PAYMENT_METHODS = {
            "alfa": "Карта (Альфа)",
            "tinkoff": "Карта (Тинькофф)",
            "cash": "Наличные",
        }
    paymentMethods = ListProperty(list(PAYMENT_METHODS.values()))
    paymentMethodSlug = StringProperty("cash")  # дефолт
    categories = ListProperty(["Продукты", "Транспорт", "Развлечения", "Прочие операции"])

    # form state
    dateText = StringProperty("2025-12-25")  # YYYY-MM-DD
    amountText = StringProperty("")
    descriptionText = StringProperty("")
    categoryText = StringProperty("Прочие операции")
    isIncome = BooleanProperty(False)

    # UI state
    isAmountValid = BooleanProperty(True)
    isLoading = BooleanProperty(False)
    statusText = StringProperty("")

    # slug for manual/cash operations
    MANUAL_SLUG = "cash"

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self.statusText = ""
        self._validate_amount(self.amountText)

    def on_back_click(self) -> None:
        if self.manager:
            self.manager.current = "transactions_upload"

    def on_payment_method_change(self, value: str) -> None:
        """
        value — текст из Spinner (человеческое название)
        """
        for slug, title in self.PAYMENT_METHODS.items():
            if title == value:
                self.paymentMethodSlug = slug
                return

    def on_date_change(self, value: str) -> None:
        self.dateText = (value or "").strip()

    def on_amount_change(self, value: str) -> None:
        self.amountText = value
        self._validate_amount(value)

    def on_description_change(self, value: str) -> None:
        self.descriptionText = value

    def on_category_change(self, value: str) -> None:
        self.categoryText = value

    def set_type(self, is_income: bool) -> None:
        self.isIncome = is_income

    def on_save_click(self) -> None:
        if self.isLoading:
            return

        self.statusText = ""

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        if not self.isAmountValid:
            self.statusText = "Введите сумму больше 0"
            return

        operation_date = (self.dateText or "").strip()
        if len(operation_date) != 10:
            self.statusText = "Дата должна быть в формате YYYY-MM-DD"
            return

        description = (self.descriptionText or "").strip()
        if not description:
            self.statusText = "Введите описание операции"
            return

        amount_abs = self._parse_amount_abs(self.amountText)
        currency_amount = amount_abs if self.isIncome else -amount_abs

        query = PostBankTransactionsQuery(slug=self.paymentMethodSlug)
        payload = PostBankTransactionsManualLoadPayload(
            operationDate=operation_date,
            description=description,
            currencyAmount=currency_amount,
        )

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        self.isLoading = True
        self.statusText = "Отправка операции…"

        self._run_request_in_thread(
            request_func=lambda: self._apiClient.post_bank_transactions(userName, password, query, payload),
            on_success=self._on_saved_success,
            on_error=self._on_saved_error,
        )

    # ----------------- callbacks -----------------
    def _on_saved_success(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, dict):
            self.statusText = "Некорректный ответ API"
            return

        loaded = payload.get("loaded rows")
        if loaded is None:
            # на всякий случай показываем весь ответ
            self.statusText = f"Успешно. Ответ: {payload}"
            return

        self.statusText = f"Успешно добавлено: {loaded}"

        # опционально: очистка формы (можешь убрать, если не надо)
        self.amountText = ""
        self.descriptionText = ""
        self._validate_amount(self.amountText)

        # опционально: вернуться назад
        # if self.manager:
        #     self.manager.current = "transactions"

    def _on_saved_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        if statusCode:
            self.statusText = f"Ошибка {statusCode}: {detail}" if detail else f"Ошибка {statusCode}"
        else:
            self.statusText = detail or "Ошибка отправки операции"

    # ----------------- helpers -----------------
    def _validate_amount(self, value: str) -> None:
        try:
            v = float((value or "").replace(",", "."))
            self.isAmountValid = v > 0
        except Exception:
            self.isAmountValid = False

    @staticmethod
    def _parse_amount_abs(value: str) -> float:
        try:
            v = float((value or "").replace(",", "."))
            return abs(v)
        except Exception:
            return 0.0

    def _run_request_in_thread(self, request_func, on_success, on_error) -> None:
        def worker() -> None:
            try:
                result = request_func()
                Clock.schedule_once(lambda _dt: on_success(result), 0)
            except requests.HTTPError as ex:
                status_code = None
                err_payload: Any = None

                try:
                    status_code = ex.response.status_code if ex.response is not None else None
                    err_payload = ex.response.json() if ex.response is not None else None
                except Exception:
                    err_payload = str(ex)

                Clock.schedule_once(lambda _dt: on_error(status_code, err_payload), 0)
            except Exception as ex:
                Clock.schedule_once(lambda _dt: on_error(None, {"detail": str(ex)}), 0)

        threading.Thread(target=worker, daemon=True).start()
