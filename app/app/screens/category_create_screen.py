from __future__ import annotations

import threading
import requests
from app.services.schema import AddCategoryPayload, AddConditionValues

from dataclasses import dataclass
from typing import Any

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService


@dataclass
class ConditionDraft:
    value: str = ""
    isExact: bool = True


class ConditionRow(BoxLayout):
    pass


class CategoryCreateScreen(Screen):
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    categoryNameText = StringProperty("")

    conditionsRvData = ListProperty([])

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._conditions: list[ConditionDraft] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self.reset_form()

    def _on_create_success(self, result: Any) -> None:
        self.isLoading = False

        self.statusText = "Категория создана."

        if self.manager is None:
            return

        try:
            categories_screen = self.manager.get_screen("categories")
            if hasattr(categories_screen, "_load_categories"):
                categories_screen._load_categories()
        except Exception:
            pass

        self.manager.current = "categories"


    def _on_create_error(self, message: str) -> None:
        self.isLoading = False
        self.statusText = message or "Ошибка создания категории."

    def on_back_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "categories"

    def reset_form(self) -> None:
        self.statusText = ""
        self.isLoading = False
        self.categoryNameText = ""

        if hasattr(self, "ids"):
            name_inp = self.ids.get("nameInput")
            if name_inp is not None:
                name_inp.text = ""

        self._conditions = [ConditionDraft(value="", isExact=True)]
        self._refresh_conditions_rv()

    def on_add_condition_click(self) -> None:
        self._conditions.append(ConditionDraft(value="", isExact=True))
        self._refresh_conditions_rv()

        if hasattr(self, "ids"):
            sv = self.ids.get("conditionsScroll")
            if sv is not None:
                Clock.schedule_once(lambda _: setattr(sv, "scroll_y", 0), 0)

    def on_remove_condition_click(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._conditions):
            return
        if len(self._conditions) == 1:
            self._conditions[0] = ConditionDraft(value="", isExact=True)
        else:
            self._conditions.pop(idx)
        self._refresh_conditions_rv()

    def on_condition_value_changed(self, idx: int, value: str) -> None:
        if idx < 0 or idx >= len(self._conditions):
            return
        self._conditions[idx].value = (value or "")

    def on_condition_exact_changed(self, idx: int, isExact: bool) -> None:
        if idx < 0 or idx >= len(self._conditions):
            return
        self._conditions[idx].isExact = bool(isExact)

    def _refresh_conditions_rv(self) -> None:
        self.conditionsRvData = [
            {
                "rowIndex": i,
                "conditionText": c.value,
                "isExact": bool(c.isExact),
                "onRemove": lambda i=i: self.on_remove_condition_click(i),
                "onText": lambda text, i=i: self.on_condition_value_changed(i, text),
                "onExact": lambda active, i=i: self.on_condition_exact_changed(i, active),
            }
            for i, c in enumerate(self._conditions)
        ]

    def on_save_click(self) -> None:
        if self.isLoading:
            return

        name = ""
        if hasattr(self, "ids"):
            name_inp = self.ids.get("nameInput")
            name = (name_inp.text if name_inp is not None else "").strip()

        if not name:
            self.statusText = "Введите название категории."
            return

        conditionValues: list[AddConditionValues] = []
        for c in self._conditions:
            v = (c.value or "").strip()
            if not v:
                continue
            conditionValues.append(AddConditionValues(conditionValue=v, isExact=bool(c.isExact)))

        if len(conditionValues) == 0:
            self.statusText = "Добавьте хотя бы одно условие."
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        payload = AddCategoryPayload(
            categoryName=name,
            conditionValues=conditionValues,
        )

        self.isLoading = True
        self.statusText = "Создание категории..."

        def worker() -> None:
            try:
                result = self._apiClient.post_category(userName=userName, password=password, payload=payload)
                Clock.schedule_once(lambda _: self._on_create_success(result), 0)
            except requests.HTTPError as ex:
                response = ex.response
                detail = ""
                try:
                    if response is not None:
                        j = response.json()
                        if isinstance(j, dict) and isinstance(j.get("detail"), str):
                            detail = j["detail"]
                except Exception:
                    pass
                Clock.schedule_once(lambda _: self._on_create_error(detail or "Ошибка создания категории"), 0)
            except Exception as ex:
                Clock.schedule_once(lambda _: self._on_create_error(str(ex)), 0)

        threading.Thread(target=worker, daemon=True).start()
