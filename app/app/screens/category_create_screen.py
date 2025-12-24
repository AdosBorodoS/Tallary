from __future__ import annotations

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
    """
    Строка условия: TextInput + CheckBox + кнопка удалить.
    Важно: никаких хитрых size/texture_size зависимостей.
    """
    pass


class CategoryCreateScreen(Screen):
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    # имя категории (храним отдельно, в UI не биндим text:)
    categoryNameText = StringProperty("")

    # данные для RecycleView условий
    conditionsRvData = ListProperty([])

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._conditions: list[ConditionDraft] = []

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self.reset_form()

    # ---------- navigation ----------
    def on_back_click(self) -> None:
        if self.manager is None:
            return
        self.manager.current = "categories"

    # ---------- form ----------
    def reset_form(self) -> None:
        self.statusText = ""
        self.isLoading = False
        self.categoryNameText = ""

        # Сбрасываем UI инпут имени
        if hasattr(self, "ids"):
            name_inp = self.ids.get("nameInput")
            if name_inp is not None:
                name_inp.text = ""

        # 1 условие по умолчанию
        self._conditions = [ConditionDraft(value="", isExact=True)]
        self._refresh_conditions_rv()

    def on_add_condition_click(self) -> None:
        self._conditions.append(ConditionDraft(value="", isExact=True))
        self._refresh_conditions_rv()

        # опционально: прокрутить вниз после добавления
        if hasattr(self, "ids"):
            sv = self.ids.get("conditionsScroll")
            if sv is not None:
                Clock.schedule_once(lambda _: setattr(sv, "scroll_y", 0), 0)

    def on_remove_condition_click(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._conditions):
            return
        # оставляем минимум 1 условие
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
        # Важно: isExact всегда bool, value всегда str
        self.conditionsRvData = [
            {
                "rowIndex": i,
                "conditionText": c.value,
                "isExact": bool(c.isExact),
                # callbacks (RecycleView-friendly)
                "onRemove": lambda i=i: self.on_remove_condition_click(i),
                "onText": lambda text, i=i: self.on_condition_value_changed(i, text),
                "onExact": lambda active, i=i: self.on_condition_exact_changed(i, active),
            }
            for i, c in enumerate(self._conditions)
        ]

    # ---------- save ----------
    def on_save_click(self) -> None:
        name = ""
        if hasattr(self, "ids"):
            name_inp = self.ids.get("nameInput")
            name = (name_inp.text if name_inp is not None else "").strip()

        # нормализуем условия: убираем пустые
        payload_conditions: list[dict[str, Any]] = []
        for c in self._conditions:
            v = (c.value or "").strip()
            if not v:
                continue
            payload_conditions.append({"conditionValue": v, "isExact": bool(c.isExact)})

        print("[CreateCategory] SAVE (stub)")
        print(f"  categoryName={name!r}")
        print(f"  conditions={payload_conditions}")

        self.statusText = "Сохранение (заглушка). Функционал будет добавлен позже."
