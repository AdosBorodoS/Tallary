from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.widgets.bottom_nav_mixin import BottomNavMixin


class CategoriesScreen(BottomNavMixin, Screen):
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    # данные для RecycleView
    rvData = ListProperty([])

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._categories: list[dict] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_categories()

    # ---------- UI handlers ----------
    def on_create_category_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "category_create"

    def on_top_plus_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "category_create"


    def on_category_click(self, category_id: int) -> None:
        print(f"Category clicked: id={category_id} (TODO: открыть детали категории)")

    # ---------- Loading / API scaffold ----------
    def _load_categories(self) -> None:
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Загрузка категорий..."
        self.rvData = []

        self._run_request_in_thread(
            request_func=self._fetch_categories_placeholder,
            on_success=self._apply_categories,
            on_error=self._handle_categories_error,
        )

    def _fetch_categories_placeholder(self) -> Any:
        """
        TODO: заменить на реальный API вызов.
        Пример ответа API (как ты прислал):
        [
          {"id":1,"categoryName":"За квартиру","categoryConditions":[...]},
          ...
        ]
        """
        return [
            {
                "id": 1,
                "categoryName": "За квартиру",
                "categoryConditions": [
                    {"id": 1, "categoryID": 1, "conditionValue": "5300448365", "isExact": True}
                ],
            },
            {
                "id": 2,
                "categoryName": "Комуналка",
                "categoryConditions": [
                    {"id": 2, "categoryID": 2, "conditionValue": "04380416", "isExact": False}
                ],
            },
            {
                "id": 3,
                "categoryName": "Еда",
                "categoryConditions": [],
            },
            {
                "id": 4,
                "categoryName": "Зарплата",
                "categoryConditions": [],
            },
        ]

    def _apply_categories(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, list):
            self.statusText = "Некорректный ответ API"
            self.rvData = []
            return

        self._categories = [x for x in payload if isinstance(x, dict)]
        self.statusText = "" if self._categories else "Категорий нет"

        # Маппинг под карточки (операции/сумма пока заглушки)
        self.rvData = [self._map_to_rv_item(item, idx) for idx, item in enumerate(self._categories)]

    def _handle_categories_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False
        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки категорий"
        self.rvData = []

    def _map_to_rv_item(self, item: dict, idx: int) -> dict:
        cid = int(item.get("id") or 0)
        name = str(item.get("categoryName") or "Без названия").strip()

        # Заглушки: тип/кол-во операций/сумма — появятся позже, когда будет API агрегатов
        # Для красоты сделаем пример: четные = расход, нечетные = доход
        is_income = (idx % 2 == 1)
        kind_text = "Доход" if is_income else "Расход"
        operations_text = "— операций"
        amount_text = "— ₽"

        return {
            "categoryId": cid,
            "titleText": name,
            "kindText": kind_text,
            "isIncome": is_income,
            "operationsText": operations_text,
            "amountText": amount_text,
        }

    # ---------- Thread helper ----------
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
