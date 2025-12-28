from __future__ import annotations

import threading
from typing import Any, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.schema import (
    AddGoalTransactionsPayload,
    DeleteGoalTransactionsPayload,
    GetTransactionGoalQuery,
)
from app.services.session_service import SessionService


class TransactionDetailsScreen(Screen):
    amountText = StringProperty("— ₽")
    descriptionText = StringProperty("—")
    bankDesc1Text = StringProperty("—")
    bankDesc2Text = StringProperty("—")
    dateText = StringProperty("—")
    accountText = StringProperty("Основной счёт")

    goals = ListProperty([])
    selectedGoalId = NumericProperty(0)
    selectedGoalName = StringProperty("—")
    isLoadingGoals = BooleanProperty(False)
    statusText = StringProperty("")

    _tx: dict | None = None
    _currentGoalId: int = 0
    _contributorUserId: int = 0

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

    def on_back_click(self) -> None:
        if self.manager:
            self.manager.current = "transactions"

    def set_transaction(self, tx: dict) -> None:
        self._tx = tx or {}

        amount = self._get_amount_value(self._tx)
        self.amountText = self._format_amount_ru(amount)

        self.descriptionText = str(self._tx.get("title") or "—")
        self.bankDesc1Text = str(self._tx.get("title") or "—")
        self.bankDesc2Text = str(self._tx.get("description2") or "—")
        self.dateText = str(self._tx.get("date") or "—")
        self.accountText = "Основной счёт"

        raw = self._get_raw_tx()
        self._contributorUserId = self._safe_int(raw.get("userID"))

        self.goals = []
        self._currentGoalId = 0
        self.selectedGoalId = 0
        self.selectedGoalName = "—"
        self.statusText = ""

        self._load_goals_and_current_goal()

    def _load_goals_and_current_goal(self) -> None:
        if self.isLoadingGoals:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        txId = self._get_transaction_id()
        slug = self._get_transaction_slug()
        if txId <= 0 or not slug:
            self.statusText = "Не удалось определить id/slug транзакции."
            return

        self.isLoadingGoals = True
        self.statusText = "Загрузка целей..."

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        def request_func() -> dict:
            goalsPayload = self._apiClient.get_goal(userName, password)

            goalQuery = GetTransactionGoalQuery(slug=slug, transactionID=txId)
            txGoalPayload = self._apiClient.get_transaction_goal(userName, password, goalQuery)

            return {"goals": goalsPayload, "txGoal": txGoalPayload}

        self._run_request_in_thread(
            request_func=request_func,
            on_success=self._on_goals_loaded,
            on_error=self._on_goals_load_error,
        )

    def _on_goals_loaded(self, payload: Any) -> None:
        self.isLoadingGoals = False

        if not isinstance(payload, dict):
            self.statusText = "Некорректный ответ при загрузке целей."
            return

        goalsList = self._extract_goal_list(payload.get("goals"))
        self.goals = goalsList

        txGoalList = self._extract_goal_list(payload.get("txGoal"))

        if txGoalList:
            currentGoal = txGoalList[0]
            self._currentGoalId = self._safe_int(currentGoal.get("id"))
            self.selectedGoalId = self._currentGoalId
            self.selectedGoalName = str(currentGoal.get("goalName") or "—")
        else:
            self._currentGoalId = 0
            self.selectedGoalId = 0
            self.selectedGoalName = "—"

        self.statusText = ""

    def _on_goals_load_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoadingGoals = False

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки целей: {detail}" if detail else "Ошибка загрузки целей"

    def set_selected_goal(self, goalId: int) -> None:
        goalIdValue = int(goalId or 0)
        self.selectedGoalId = goalIdValue
        self.selectedGoalName = self._goal_name_by_id(goalIdValue)

    def _goal_name_by_id(self, goalId: int) -> str:
        if goalId <= 0:
            return "—"
        for goalItem in (self.goals or []):
            if self._safe_int(goalItem.get("id")) == goalId:
                return str(goalItem.get("goalName") or "—")
        return "—"

    def on_goal_spinner_change(self, selectedText: str) -> None:
        textValue = (selectedText or "").strip()

        if textValue == "—" or textValue == "":
            self.set_selected_goal(0)
            return

        goalId = self._goal_id_by_name(textValue)
        self.set_selected_goal(goalId)

    def _goal_id_by_name(self, goalName: str) -> int:
        normalizedName = (goalName or "").strip()
        for goalItem in (self.goals or []):
            if str(goalItem.get("goalName") or "").strip() == normalizedName:
                return self._safe_int(goalItem.get("id"))
        return 0

    def on_save_click(self) -> None:
        if self.isLoadingGoals:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        txId = self._get_transaction_id()
        slug = self._get_transaction_slug()
        if txId <= 0 or not slug:
            self.statusText = "Не удалось определить id/slug транзакции."
            return

        newGoalId = int(self.selectedGoalId or 0)
        oldGoalId = int(self._currentGoalId or 0)

        if newGoalId == oldGoalId:
            self.statusText = "Изменений нет."
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        self.isLoadingGoals = True
        self.statusText = "Сохранение..."

        def request_func() -> Any:
            deletePayload = DeleteGoalTransactionsPayload(transactionID=txId, slug=slug)
            self._apiClient.delete_goal_transactions(userName, password, deletePayload)

            if newGoalId > 0:
                addPayload = AddGoalTransactionsPayload(
                    goalID=newGoalId,
                    transactionID=txId,
                    transactionSource=slug,
                    contributorUserID=int(self._contributorUserId or 0),
                )
                self._apiClient.post_goal_transactions(userName, password, addPayload)

            return {"ok": True}

        def on_success(_: Any) -> None:
            self.isLoadingGoals = False
            self.statusText = "Сохранено."

            self._currentGoalId = newGoalId
            self.selectedGoalName = self._goal_name_by_id(newGoalId) if newGoalId > 0 else "—"

        def on_error(statusCode: Optional[int], errorPayload: Any) -> None:
            self.isLoadingGoals = False
            detail = ""
            if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
                detail = errorPayload["detail"].strip()
            self.statusText = f"Ошибка сохранения: {detail}" if detail else "Ошибка сохранения"

        self._run_request_in_thread(
            request_func=request_func,
            on_success=on_success,
            on_error=on_error,
        )

    def _get_raw_tx(self) -> dict:
        raw = self._tx.get("raw") if isinstance(self._tx, dict) else None
        return raw if isinstance(raw, dict) else {}

    def _get_transaction_id(self) -> int:
        if isinstance(self._tx, dict) and self._tx.get("id") is not None:
            return self._safe_int(self._tx.get("id"))
        return self._safe_int(self._get_raw_tx().get("id"))

    def _get_transaction_slug(self) -> str:
        if isinstance(self._tx, dict):
            slug = self._tx.get("slug")
            if isinstance(slug, str) and slug.strip():
                return slug.strip()
        slugRaw = self._get_raw_tx().get("slug")
        return str(slugRaw or "").strip()

    @staticmethod
    def _extract_goal_list(payload: Any) -> list[dict]:
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            return [x for x in payload["data"] if isinstance(x, dict)]
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        return []

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _get_amount_value(tx: dict) -> float:
        raw_value = tx.get("amount")
        try:
            return float(raw_value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _format_amount_ru(amount: float) -> str:
        sign = "+" if amount > 0 else "−" if amount < 0 else ""
        value = abs(amount)

        if float(value).is_integer():
            as_str = f"{int(value):,}".replace(",", " ")
        else:
            as_str = f"{value:,.2f}".replace(",", " ").replace(".", ",")

        return f"{sign} {as_str} ₽".strip()

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
