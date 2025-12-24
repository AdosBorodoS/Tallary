from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Callable, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.widgets.bottom_nav_mixin import BottomNavMixin


class TransactionsScreen(BottomNavMixin, Screen):
    searchText = StringProperty("")
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    canLoadMore = BooleanProperty(True)

    # data for RecycleView
    rvData = ListProperty([])

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._transactions: list[dict] = []   # normalized
        self._page = 1

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._page = 1
        self._load_transactions(reset=True)

    # ---------- UI handlers ----------
    def on_search_text(self, value: str) -> None:
        self.searchText = value
        self._apply_filters()

    def on_filter_date_click(self) -> None:
        print("Filter: date clicked (TODO)")
        # TODO: open date picker

    def on_filter_category_click(self) -> None:
        print("Filter: category clicked (TODO)")
        # TODO: open category picker

    def on_filter_type_click(self) -> None:
        print("Filter: type clicked (TODO)")
        # TODO: open type picker

    def on_item_click(self, item: dict) -> None:
        """
        Клик по транзакции -> открыть детали.
        """
        if self.manager is None:
            return

        try:
            details = self.manager.get_screen("transaction_details")
        except Exception:
            print("No screen 'transaction_details' in ScreenManager")
            return

        # передаём объект в детали
        if hasattr(details, "set_transaction"):
            details.set_transaction(item)
        self.manager.current = "transaction_details"

    def on_load_more_click(self) -> None:
        """
        Клик по строке 'Загрузить старых...' (пока рыба).
        """
        print("Load more clicked (TODO pagination)")
        if self.isLoading:
            return
        self._page += 1
        self._load_transactions(reset=False)

    def on_upload_transactions_click(self) -> None:
        """Открыть экран загрузки транзакций (пока заглушка)."""
        if self.manager is None:
            return
        self.manager.current = "transactions_upload"

    # ---------- Loading / API scaffold ----------
    def _load_transactions(self, reset: bool) -> None:
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Загрузка транзакций..."
        if reset:
            self.rvData = []
            self._transactions = []

        self._run_request_in_thread(
            request_func=lambda: self._fetch_transactions_payload_placeholder(page=self._page),
            on_success=lambda payload: self._apply_transactions_payload(payload, append=(not reset)),
            on_error=self._handle_transactions_error,
        )

    def _fetch_transactions_payload_placeholder(self, page: int) -> dict:
        """
        TODO: заменить на реальный API вызов.
        Возвращает payload как ты прислал: {"alfa":[...], "tinkoff":[...], "cash":[...]}
        """
        # page сейчас просто имитируем (на 2-й странице вернём пусто)
        if page >= 2:
            return {"alfa": [], "tinkoff": [], "cash": []}

        return {
            "alfa": [
                {
                    "operationDate": "2025-10-31",
                    "postingDate": "1970-01-01",
                    "category": "Прочие операции",
                    "currencyAmount": -1081,
                    "description": "YANDEX LAVKA, MCC: 5411",
                    "description2": "OPLATA YANDEX",
                    "status": None,
                },
                {
                    "operationDate": "2025-10-31",
                    "postingDate": "2025-10-31",
                    "category": "Прочие операции",
                    "currencyAmount": 5000,
                    "description": "Внутрибанковский перевод между счетами",
                    "description2": "KARTA XXX1234",
                    "status": "Выполнен",
                },
            ],
            "tinkoff": [
                {
                    "operationDate": "2025-09-26",
                    "postingDate": "2025-09-26",
                    "currencyAmount": 1734,
                    "description": "Пополнение. Система быстрых платежей",
                    "description2": None,
                    "category": "Прочие доходы",
                },
                {
                    "operationDate": "2025-09-12",
                    "postingDate": "2025-09-12",
                    "currencyAmount": -280,
                    "description": "Обед в столовой",
                    "description2": None,
                    "category": "Еда",
                },
            ],
            "cash": [],
        }

    def _apply_transactions_payload(self, payload: Any, append: bool) -> None:
        self.isLoading = False

        if not isinstance(payload, dict):
            self.statusText = "Некорректный ответ API"
            self.rvData = []
            self.canLoadMore = False
            return

        normalized = self._normalize_payload(payload)

        if append:
            self._transactions.extend(normalized)
        else:
            self._transactions = normalized

        # “canLoadMore” пока условно: если пришло меньше 1 элемента — больше нет страниц
        self.canLoadMore = len(normalized) > 0

        self.statusText = "" if len(self._transactions) else "Нет транзакций"
        self._apply_filters()

    def _handle_transactions_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False
        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки транзакций"
        self.rvData = []
        self.canLoadMore = False

    # ---------- Filtering / mapping ----------
    def _apply_filters(self) -> None:
        query = (self.searchText or "").strip().lower()

        items = self._transactions
        if query:
            items = [
                t for t in items
                if query in (t.get("title") or "").lower()
                or query in (t.get("category") or "").lower()
                or query in (t.get("description2") or "").lower()
            ]

        self.rvData = [self._map_to_rv_item(t) for t in items]

    def _normalize_payload(self, payload: dict) -> list[dict]:
        """
        Сводим alfa/tinkoff/cash в один список:
        {
          "date": "YYYY-MM-DD",
          "title": "...",
          "category": "...",
          "amount": int,
          "source": "alfa|tinkoff|cash",
          "description2": "...",
          "status": "...",
          "raw": dict,
        }
        """
        out: list[dict] = []

        def add_item(source: str, row: dict) -> None:
            date_value = str(row.get("operationDate") or row.get("postingDate") or "")[:10]
            title_value = str(row.get("description") or "").strip()
            category_value = str(row.get("category") or "Прочие операции").strip()
            description2_value = row.get("description2")
            status_value = row.get("status")

            amount_value = row.get("currencyAmount")
            try:
                amount_int = int(float(amount_value)) if amount_value is not None else 0
            except Exception:
                amount_int = 0

            if not title_value:
                title_value = "Операция"

            out.append({
                "date": date_value,
                "title": title_value,
                "category": category_value,
                "amount": amount_int,
                "source": source,
                "description2": "" if description2_value is None else str(description2_value),
                "status": "" if status_value is None else str(status_value),
                "raw": row,
            })

        for row in payload.get("alfa") or []:
            if isinstance(row, dict):
                add_item("alfa", row)

        for row in payload.get("tinkoff") or []:
            if isinstance(row, dict):
                add_item("tinkoff", row)

        for row in payload.get("cash") or []:
            if isinstance(row, dict):
                add_item("cash", row)

        out.sort(key=lambda x: x.get("date") or "", reverse=True)
        return out

    def _map_to_rv_item(self, item: dict) -> dict:
        date_label = self._format_date_ru(item.get("date") or "")
        title = item.get("title") or "Операция"
        category = item.get("category") or "Прочие операции"
        amount = int(item.get("amount") or 0)

        # внутренние переводы — белые (neutral)
        title_l = title.lower()
        is_internal_transfer = ("внутрибанков" in title_l) or ("перевод" in title_l)

        is_income = amount > 0
        is_neutral = is_internal_transfer  # ключевая правка
        amount_text = self._format_amount(amount)

        return {
            # текст
            "dateText": date_label,
            "titleText": title,
            "categoryText": category,
            "amountText": amount_text,

            # признаки для цвета
            "isIncome": bool(is_income),
            "isNeutral": bool(is_neutral),

            # клик
            "on_release": (lambda it=item: self.on_item_click(it)),
        }

    def _format_amount(self, amount: int) -> str:
        sign = "+" if amount > 0 else "−" if amount < 0 else ""
        value = abs(amount)
        formatted = f"{value:,}".replace(",", " ")
        return f"{sign} {formatted} ₽".strip()

    def _format_date_ru(self, iso_date: str) -> str:
        try:
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
        except Exception:
            return iso_date

        months = {
            1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
            7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
        }
        return f"{dt.day:02d} {months.get(dt.month, '')}".strip()

    # ---------- Thread helper ----------
    def _safe_extract_response_payload(self, response: Optional[requests.Response]) -> Any:
        if response is None:
            return {"detail": "No response"}
        try:
            return response.json()
        except Exception:
            text_value = (response.text or "").strip()
            return {"detail": text_value} if text_value else {"detail": f"HTTP {response.status_code}"}

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
                status_code = response.status_code if response is not None else None
                payload = self._safe_extract_response_payload(response=response)
                Clock.schedule_once(lambda _: on_error(status_code, payload), 0)
                return
            except Exception as ex:
                Clock.schedule_once(lambda _: on_error(None, {"detail": str(ex)}), 0)

        threading.Thread(target=worker, daemon=True).start()
