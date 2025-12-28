from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import threading
import requests

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.services.schema import (
    DeleteCategoryQuery,
    PatchCategoryQuery,
    UpdateDataServiceSchemaPayLoad,
    UpdateConditionValues,
    AddCategoryConditionPayload,
    DeleteCategoryConditionQeury,
    DeleteCategoryConditionPayload,
)


@dataclass
class EditConditionDraft:
    conditionId: int = 0
    value: str = ""
    isExact: bool = True


class EditConditionRow(BoxLayout):
    pass


class CategoryEditScreen(Screen):
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    categoryId = NumericProperty(0)
    categoryNameText = StringProperty("")

    conditionsRvData = ListProperty([])

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService
        self._deletedConditionIds: set[int] = set()

        self._conditions: list[EditConditionDraft] = []
        self._categoryLoaded: bool = False

        self._originalConditionIds: set[int] = set()

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        if not self._categoryLoaded:
            self._reset_empty_state()

    def on_back_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "categories"

    def set_category(self, categoryItem: dict) -> None:
        try:
            self.categoryId = int(categoryItem.get("id") or 0)
        except Exception:
            self.categoryId = 0

        self.categoryNameText = str(categoryItem.get("categoryName") or "").strip()

        rawConditions = categoryItem.get("categoryConditions")
        if not isinstance(rawConditions, list):
            rawConditions = []

        self._conditions = []
        self._originalConditionIds = set()
        self._deletedConditionIds = set()

        for c in rawConditions:
            if not isinstance(c, dict):
                continue

            try:
                condId = int(c.get("id") or 0)
            except Exception:
                condId = 0

            value = str(c.get("conditionValue") or "")
            isExact = bool(c.get("isExact"))

            self._conditions.append(EditConditionDraft(conditionId=condId, value=value, isExact=isExact))
            if condId != 0:
                self._originalConditionIds.add(condId)

        if len(self._conditions) == 0:
            self._conditions = [EditConditionDraft(conditionId=0, value="", isExact=True)]

        if hasattr(self, "ids"):
            name_inp = self.ids.get("nameInput")
            if name_inp is not None:
                name_inp.text = self.categoryNameText

        self.statusText = ""
        self.isLoading = False
        self._categoryLoaded = True

        self._refresh_conditions_rv()

        if hasattr(self, "ids"):
            sv = self.ids.get("conditionsScroll")
            if sv is not None:
                Clock.schedule_once(lambda _: setattr(sv, "scroll_y", 1), 0)

    def _reset_empty_state(self) -> None:
        self.statusText = ""
        self.isLoading = False
        self.categoryId = 0
        self.categoryNameText = ""
        self._originalConditionIds = set()

        if hasattr(self, "ids"):
            name_inp = self.ids.get("nameInput")
            if name_inp is not None:
                name_inp.text = ""

        self._conditions = [EditConditionDraft(conditionId=0, value="", isExact=True)]
        self._refresh_conditions_rv()

    def on_add_condition_click(self) -> None:
        self._conditions.append(EditConditionDraft(conditionId=0, value="", isExact=True))
        self._refresh_conditions_rv()

        if hasattr(self, "ids"):
            sv = self.ids.get("conditionsScroll")
            if sv is not None:
                Clock.schedule_once(lambda _: setattr(sv, "scroll_y", 0), 0)

    def on_remove_condition_click(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._conditions):
            return

        removed = self._conditions[idx]

        if int(removed.conditionId) != 0:
            self._deletedConditionIds.add(int(removed.conditionId))

        if len(self._conditions) == 1:
            self._conditions[0] = EditConditionDraft(conditionId=0, value="", isExact=True)
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
                "conditionText": str(c.value or ""),
                "isExact": bool(c.isExact),
                "onText": lambda text, i=i: self.on_condition_value_changed(i, text),
                "onExact": lambda active, i=i: self.on_condition_exact_changed(i, active),
                "onRemove": lambda i=i: self.on_remove_condition_click(i),
            }
            for i, c in enumerate(self._conditions)
        ]

    def _get_auth(self) -> tuple[str, str]:
        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password
        return userName, password

    def _refresh_categories_screen(self) -> None:
        if self.manager is None:
            return
        try:
            categoriesScreen = self.manager.get_screen("categories")
            if hasattr(categoriesScreen, "_load_categories"):
                categoriesScreen._load_categories()
        except Exception:
            pass

    def on_delete_click(self) -> None:
        if self.isLoading:
            return

        self.isLoading = True
        self.statusText = "Удаление категории..."

        def worker() -> None:
            try:
                userName, password = self._get_auth()
                query = DeleteCategoryQuery(categoryID=int(self.categoryId))
                self._apiClient.delete_category(userName=userName, password=password, qeury=query)

                Clock.schedule_once(lambda _: self._on_delete_success(), 0)
            except requests.HTTPError as ex:
                Clock.schedule_once(lambda _: self._on_error_from_http(ex, "Ошибка удаления категории"), 0)
            except Exception as ex:
                Clock.schedule_once(lambda _: self._on_error(str(ex) or "Ошибка удаления категории"), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _on_delete_success(self) -> None:
        self.isLoading = False
        self.statusText = "Категория удалена."
        self._refresh_categories_screen()

        if self.manager is not None:
            self.manager.current = "categories"

    def on_save_click(self) -> None:
        if self.isLoading:
            return

        name = ""
        if hasattr(self, "ids"):
            name_inp = self.ids.get("nameInput")
            name = (name_inp.text if name_inp is not None else "").strip()

        normalized: list[EditConditionDraft] = []
        for c in self._conditions:
            v = (c.value or "").strip()
            if not v:
                continue
            normalized.append(EditConditionDraft(conditionId=int(c.conditionId), value=v, isExact=bool(c.isExact)))

        existing = [c for c in normalized if c.conditionId != 0]
        newOnes = [c for c in normalized if c.conditionId == 0]

        deletedIds = sorted(list(self._deletedConditionIds))

        self.isLoading = True
        self.statusText = "Сохранение..."

        def worker() -> None:
            try:
                userName, password = self._get_auth()
                categoryId = int(self.categoryId)

                patchQuery = PatchCategoryQuery(categoryID=categoryId)

                payload = UpdateDataServiceSchemaPayLoad(
                    categoryName=name,
                    conditionValues=[
                        UpdateConditionValues(
                            conditionID=int(c.conditionId),
                            conditionValue=str(c.value),
                            isExact=bool(c.isExact),
                        )
                        for c in existing
                    ],
                )
                self._apiClient.patch_category(userName=userName, password=password, qeury=patchQuery, payload=payload)

                for c in newOnes:
                    addPayload = AddCategoryConditionPayload(
                        categoryID=categoryId,
                        conditionValue=str(c.value),
                        isExact=bool(c.isExact),
                    )
                    self._apiClient.add_category_condition(userName=userName, password=password, payload=addPayload)

                for conditionId in deletedIds:
                    delQuery = DeleteCategoryConditionQeury(categoryID=categoryId)
                    delPayload = DeleteCategoryConditionPayload(conditionID=int(conditionId))
                    self._apiClient.delete_category_condition(
                        userName=userName,
                        password=password,
                        query=delQuery,
                        payload=delPayload,
                    )

                Clock.schedule_once(lambda _: self._on_save_success(), 0)

            except requests.HTTPError as ex:
                Clock.schedule_once(lambda _: self._on_error_from_http(ex, "Ошибка сохранения"), 0)
            except Exception as ex:
                Clock.schedule_once(lambda _: self._on_error(str(ex) or "Ошибка сохранения"), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _on_save_success(self) -> None:
        self.isLoading = False
        self.statusText = "Изменения сохранены."
        self._refresh_categories_screen()

        if self.manager is not None:
            self.manager.current = "categories"
        
        self._deletedConditionIds = set()

    def _on_error_from_http(self, ex: requests.HTTPError, fallback: str) -> None:
        detail = ""
        try:
            if ex.response is not None:
                j = ex.response.json()
                if isinstance(j, dict) and isinstance(j.get("detail"), str):
                    detail = j["detail"]
        except Exception:
            pass
        self._on_error(detail or fallback)

    def _on_error(self, message: str) -> None:
        self.isLoading = False
        self.statusText = message
