from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.services.schema import GetCategoryTransactionsQeury
from app.widgets.bottom_nav_mixin import BottomNavMixin


class TransactionsScreen(BottomNavMixin, Screen):
    searchText = StringProperty("")
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    visibleLimit = NumericProperty(15)
    canLoadMore = BooleanProperty(False)

    sortField = StringProperty("date")
    isCategoryAsc = BooleanProperty(True)
    isTypeAsc = BooleanProperty(True) 
    isDateDesc = BooleanProperty(True)

    rvData = ListProperty([])

    TRANSACTION_SLUGS = "alfa,tinkoff,cash"

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._allTransactions: list[dict] = []
        self._filteredTransactions: list[dict] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)

        self.visibleLimit = 15
        self.searchText = ""
        self.statusText = ""

        self._load_transactions()

    def on_search_text(self, value: str) -> None:
        self.searchText = value
        self._apply_filters_and_refresh()

    def on_logout_button_click(self) -> None:
        self._sessionService.clear()
        self.on_nav_click("login")

    def on_friends_button_click(self) -> None:
        self.on_nav_click("friends")

    def on_transaction_click(self, tx: dict) -> None:
        """
        Открывает экран детализации и прокидывает туда normalized transaction dict.
        """
        if self.manager is None:
            return

        detailsScreen = self.manager.get_screen("transaction_details")


        if detailsScreen is None:
            print("[TransactionsScreen] TransactionDetailsScreen not found in ScreenManager")
            return

        if hasattr(detailsScreen, "set_transaction"):
            detailsScreen.set_transaction(tx)

        self.manager.current = detailsScreen.name

    @staticmethod
    def _getAmountValue(transactionItem: dict) -> float:
        rawValue = transactionItem.get("currencyAmount")
        try:
            return float(rawValue or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _typeSortKey(self, transactionItem: dict) -> int:
        amountValue = self._getAmountValue(transactionItem)

        if amountValue < 0:
            return 0
        if amountValue == 0:
            return 1
        return 2

    @staticmethod
    def _categorySortKey(transactionItem: dict) -> str:
        value = (
            transactionItem.get("customCategory")
            or transactionItem.get("category")
            or transactionItem.get("bankCategory")
            or ""
        )
        return str(value).strip().lower()

    def on_filter_date_click(self) -> None:
        self.isDateDesc = not self.isDateDesc
        self._apply_filters_and_refresh()

    def on_filter_category_click(self) -> None:
        self.sortField = "category"
        self.isCategoryAsc = not self.isCategoryAsc
        self._apply_filters_and_refresh()

    def on_filter_type_click(self) -> None:
        self.sortField = "type"
        self.isTypeAsc = not self.isTypeAsc
        self._apply_filters_and_refresh()

    def on_load_more_click(self) -> None:
        if self.isLoading:
            return

        self.visibleLimit += 15
        self._apply_filters_and_refresh()

    def on_upload_transactions_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "transactions_upload"

    def _load_transactions(self) -> None:
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            self.rvData = []
            self.canLoadMore = False
            return

        self.isLoading = True
        self.statusText = "Загрузка транзакций..."
        self.rvData = []
        self._allTransactions = []
        self._filteredTransactions = []

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        query = GetCategoryTransactionsQeury(slugs=self.TRANSACTION_SLUGS)

        self._run_request_in_thread(
            request_func=lambda: self._apiClient.get_category_transactions(userName, password, query),
            on_success=self._on_transactions_loaded,
            on_error=self._handle_transactions_error,
        )

    def _on_transactions_loaded(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, dict):
            self.statusText = "Некорректный ответ API"
            self.rvData = []
            self.canLoadMore = False
            return

        data = payload.get("data")
        if not isinstance(data, list):
            self.statusText = "Некорректный ответ API: нет data[]"
            self.rvData = []
            self.canLoadMore = False
            return

        self._allTransactions = self._normalize_api_transactions(data)

        if not self._allTransactions:
            self.statusText = "Нет транзакций"
            self.rvData = []
            self.canLoadMore = False
            return

        self.statusText = ""
        self._apply_filters_and_refresh()

    def _handle_transactions_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки транзакций"
        self.rvData = []
        self.canLoadMore = False

    # ---------- Filtering / sorting / mapping ----------
    def _apply_filters_and_refresh(self) -> None:
        query = (self.searchText or "").strip().lower()

        items = self._allTransactions

        def getCategoryValue(t: dict) -> str:
            value = (t.get("customCategory") or t.get("category") or t.get("bankCategory") or "")
            return str(value).strip().lower()

        def getAmountValue(t: dict) -> float:
            rawValue = t.get("currencyAmount")
            try:
                return float(rawValue or 0.0)
            except (TypeError, ValueError):
                return 0.0

        def typeSortKey(t: dict) -> int:
            amountValue = getAmountValue(t)
            if amountValue < 0:
                return 0
            if amountValue == 0:
                return 1
            return 2

        if query:
            def haystack(t: dict) -> str:
                return " ".join([
                    str(t.get("title") or ""),
                    str(t.get("description") or ""),
                    str(t.get("description2") or ""),
                    str(t.get("code") or ""),
                    str(t.get("customCategory") or ""),
                    str(t.get("category") or ""),
                    str(t.get("bankCategory") or ""),
                ]).lower()

            items = [t for t in items if query in haystack(t)]

        items = list(items)

        sortField = (getattr(self, "sortField", None) or "date").strip().lower()

        if sortField == "category":
            items.sort(key=getCategoryValue, reverse=not self.isCategoryAsc)

        elif sortField == "type":
            items.sort(key=lambda t: t.get("_dateKey", 0), reverse=self.isDateDesc)
            items.sort(key=typeSortKey, reverse=not self.isTypeAsc)

        else:
            items.sort(key=lambda t: t.get("_dateKey", 0), reverse=self.isDateDesc)

        self._filteredTransactions = items

        visible = items[: int(self.visibleLimit)]
        self.canLoadMore = len(items) > len(visible)

        self.rvData = [self._map_to_rv_item(t) for t in visible]

        if not self.rvData:
            self.statusText = "Ничего не найдено" if query else "Нет транзакций"
        else:
            self.statusText = ""
    # ---------- Filtering / sorting / mapping ----------
    
    
    def _normalize_api_transactions(self, rows: list[dict]) -> list[dict]:
        out: list[dict] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            dateStr = (row.get("operationDate") or row.get("postingDate") or "")[:10]
            dateKey = self._safe_date_key(dateStr)

            categoryValue = (
                row.get("customCategory")
                or row.get("category")
                or row.get("bankCategory")
                or "Прочие операции"
            )
            categoryValue = str(categoryValue).strip() if categoryValue is not None else "Прочие операции"

            titleValue = str(row.get("description") or "").strip()
            if not titleValue:
                titleValue = "Операция"

            description2Value = row.get("description2")
            description2_text = "" if description2Value is None else str(description2Value).strip()

            amountValue = row.get("amount")
            if amountValue is None:
                amountValue = row.get("currencyAmount")

            amountNum = self._safe_float(amountValue)

            out.append({
                "date": dateStr,
                "_dateKey": dateKey,
                "title": titleValue,
                "category": categoryValue,
                "amount": amountNum,
                "description2": description2_text,
                "raw": row,
            })

        return out

    @staticmethod
    def _safe_date_key(dateStr: str) -> int:
        try:
            dt = datetime.strptime(dateStr, "%Y-%m-%d")
            return int(dt.timestamp())
        except Exception:
            return 0

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _map_to_rv_item(self, t: dict) -> dict:
        amount = float(t.get("amount") or 0.0)

        is_income = amount > 0
        is_neutral = amount == 0

        date_text = t.get("date") or ""
        amount_text = self._format_amount(amount)

        return {
            "dateText": date_text,
            "titleText": t.get("title") or "",
            "categoryText": t.get("category") or "Прочие операции",
            "amountText": amount_text,
            "isIncome": is_income,
            "isNeutral": is_neutral,

            # ключевое: передаём callback в TransactionItem
            # фиксируем t через default arg, чтобы не было late-binding бага
            "onPress": (lambda tx=t: self.on_transaction_click(tx)),
        }

    @staticmethod
    def _format_amount(value: float) -> str:
        sign = "+" if value > 0 else ""
        if abs(value - int(value)) < 1e-9:
            return f"{sign}{int(value)} ₽"
        return f"{sign}{value:.2f} ₽"

    # ---------- threading helper ----------
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
