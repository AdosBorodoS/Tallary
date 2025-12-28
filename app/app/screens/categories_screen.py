from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.widgets.bottom_nav_mixin import BottomNavMixin


class CategoryItemRow(RecycleDataViewBehavior, ButtonBehavior, BoxLayout):
    categoryId = NumericProperty(0)
    titleText = StringProperty("")
    kindText = StringProperty("")
    isIncome = BooleanProperty(False)
    operationsText = StringProperty("")
    amountText = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        self.rv = rv
        return super().refresh_view_attrs(rv, index, data)

    def on_release(self):
        rv = getattr(self, "rv", None)
        screen = getattr(rv, "screen", None) if rv is not None else None

        if screen is None:
            print("[CategoryItemRow] Click ignored: rv.screen not bound")
            return

        screen.on_category_click(int(self.categoryId))


class CategoriesScreen(BottomNavMixin, Screen):
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    rvData = ListProperty([])

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._categories: list[dict] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_categories()

    def on_create_category_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "category_create"

    def on_top_plus_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "category_create"

    def on_category_click(self, category_id: int) -> None:
        if self.manager is None:
            return

        category_item = self._get_category_by_id(category_id=category_id)
        if category_item is None:
            print(f"[Categories] Category not found: id={category_id}")
            return

        try:
            edit_screen = self.manager.get_screen("category_edit")
            if hasattr(edit_screen, "set_category"):
                edit_screen.set_category(category_item)
        except Exception as ex:
            print(f"[Categories] Failed to open edit screen: {ex}")
            return

        self.manager.current = "category_edit"

    def _get_category_by_id(self, category_id: int) -> Optional[dict]:
        for item in self._categories:
            try:
                if int(item.get("id") or 0) == int(category_id):
                    return item
            except Exception:
                continue
        return None

    def _load_categories(self) -> None:
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Загрузка категорий..."
        self.rvData = []

        if hasattr(self, "ids") and "rvCategories" in self.ids:
            self.ids.rvCategories.screen = self

        self._run_request_in_thread(
            request_func=self._fetch_categories_from_api,
            on_success=self._apply_categories,
            on_error=self._handle_categories_error,
        )

    def _fetch_categories_from_api(self) -> Any:
        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        if not userName or not password:
            raise Exception("Нет данных авторизации (userName/password) в SessionService")

        return self._apiClient.get_category(userName=userName, password=password)

    def _apply_categories(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, list):
            self.statusText = "Некорректный ответ API"
            self.rvData = []
            return

        self._categories = [x for x in payload if isinstance(x, dict)]
        self.statusText = "" if self._categories else "Категорий нет"

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

        transactionsCount = int(item.get("transactionsCount") or 0)

        try:
            amountSum = float(item.get("amountSum") or 0.0)
        except Exception:
            amountSum = 0.0

        is_income = (idx % 2 == 1)
        kind_text = "Доход" if is_income else "Расход"

        operations_text = f"{transactionsCount} операций"
        amount_text = f"{amountSum:,.0f} ₽".replace(",", " ")

        return {
            "categoryId": cid,
            "titleText": name,
            "kindText": kind_text,
            "isIncome": is_income,
            "operationsText": operations_text,
            "amountText": amount_text,
        }

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
