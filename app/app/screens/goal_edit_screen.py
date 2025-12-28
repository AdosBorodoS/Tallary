from __future__ import annotations

import json
import threading
from typing import Any, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from app.widgets.bottom_nav_mixin import BottomNavMixin
from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.services.schema import (
    DeleteGoalQuery,
    DeleteGoalOperatorQuery,
    GaolParticipant,
    GetGoalParticipant,
    GetGoalTransactionsQuery,
    ParticipantCatalog,
    PostGoalOperatorsPayload,
    PostGoalOperatorsQuery,
    GetGoalOperatorsQuery
)

class FriendPickPopupContent(BoxLayout):
    screen = ObjectProperty(None)


class GoalEditScreen(BottomNavMixin, Screen):
    goalId = NumericProperty(0)

    titleText = StringProperty("Моя цель")
    goalNameText = StringProperty("")
    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    conditionsData = ListProperty([])
    participantsData = ListProperty([])
    goalTransactionsData = ListProperty([]) 

    friendSearchText = StringProperty("")
    friendsData = ListProperty([])
    selectedFriendId = NumericProperty(0)
    selectedFriendName = StringProperty("")



    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._friendsPopup = None
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._friendsCache: list[dict[str, Any]] = []
        self._participantsCache: list[dict[str, Any]] = []
        self._operatorsCache: list[dict[str, Any]] = []

        self._originalParticipantIds: set[int] = set()
        self._originalOperators: list[dict[str, Any]] = []

        self._goalMeta: dict[str, Any] = {}

    def load_goal(self, goalId: int, goalName: str = "", goalMeta: Optional[dict[str, Any]] = None) -> None:
        goalMetaValue: dict[str, Any] = goalMeta if isinstance(goalMeta, dict) else {}

        try:
            goalIdValue = int(goalId or 0)
        except (TypeError, ValueError):
            goalIdValue = 0

        goalMetaValue: dict[str, Any] = goalMeta if isinstance(goalMeta, dict) else {}

        goalNameValue = str(goalName or "").strip()
        if not goalNameValue:
            goalNameValue = str(goalMetaValue.get("goalName") or "").strip()

        self.goalId = goalIdValue
        self.goalMeta = goalMetaValue

        self.goalNameText = goalNameValue
        self.titleText = f"Моя Цель: {self.goalNameText}" if self.goalNameText else "Моя цель"

        self.conditionsData = []
        self.participantsData = []
        self.friendsData = []

        transactionsRaw = goalMetaValue.get("transactions")
        if not isinstance(transactionsRaw, list):
            transactionsRaw = []

        self.goalTransactionsData = self._build_goal_transactions_rv_data(transactionsRaw)

        transactionsRvData: list[dict[str, Any]] = []
        for item in transactionsRaw:
            if not isinstance(item, dict):
                continue

            userNameValue = str(item.get("userName") or "").strip()

            amountValue = item.get("currencyAmount")
            try:
                amountNumber = float(amountValue or 0)
            except (TypeError, ValueError):
                amountNumber = 0.0

            amountTextValue = f"{amountNumber:,.0f}".replace(",", " ")

            dateTextValue = str(item.get("operationDate") or "").strip()

            transactionsRvData.append(
                {
                    "userName": userNameValue,
                    "amountText": amountTextValue,
                    "dateText": dateTextValue,
                    "goalTransactionID": int(item.get("goalTransactionID") or 0),
                    "raw": item,
                }
            )

        self.goalTransactionsData = transactionsRvData
        Clock.schedule_once(lambda _: self._load_goal_from_api(), 0)


    @property
    def goalMeta(self) -> dict[str, Any]:
        return self._goalMeta

    @goalMeta.setter
    def goalMeta(self, value: dict[str, Any]) -> None:
        self._goalMeta = value or {}

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)

        if "friendsPopup" in self.ids:
            try:
                self.ids.friendsPopup.dismiss()
            except Exception:
                pass

        if self.goalId > 0 and (not self.conditionsData and not self.participantsData):
            self._load_goal_from_api()


    @staticmethod
    def _format_amount(amountValue: Any) -> str:
        try:
            amountNumber = float(amountValue or 0)
        except (TypeError, ValueError):
            amountNumber = 0.0
        return f"{amountNumber:,.0f}".replace(",", " ")

    def _build_goal_transactions_rv_data(self, transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []

        for item in transactions:
            if not isinstance(item, dict):
                continue

            userName = str(item.get("userName") or "").strip()

            amountRaw = item.get("currencyAmount", item.get("amount", 0))
            try:
                amountValue = float(amountRaw or 0)
            except Exception:
                amountValue = 0.0

            operationDate = str(
                item.get("operationDate")
                or item.get("postingDate")
                or item.get("date")
                or ""
            ).strip()

            amountText = f"{amountValue:+.2f}" if amountValue else "0.00"

            data.append(
                {
                    "screen": self,
                    "userName": userName,
                    "amountText": amountText,
                    "dateText": operationDate,
                    "raw": item,
                }
            )

        return data

    def _load_goal_from_api(self) -> None:
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        if self.goalId <= 0:
            self.statusText = "Не указан goalId."
            return

        self.isLoading = True
        self.statusText = "Загрузка..."
        self.conditionsData = []
        self.participantsData = []
        self.friendsData = []

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password
        goalId = int(self.goalId)

        def request_func() -> dict[str, Any]:
            goalsPayload = self._apiClient.get_goal(userName, password)

            operatorsPayload = self._apiClient.get_goal_operator(
                userName,
                password,
                GetGoalOperatorsQuery(goalID=goalId),
            )

            participantsPayload = self._apiClient.get_goal_participant(
                userName,
                password,
                GetGoalParticipant(goalID=goalId),
            )

            friendsPayload = self._apiClient.get_friends(userName, password)

            transactionsPayload = self._apiClient.get_goal_transactions(
                userName,
                password,
                GetGoalTransactionsQuery(goalID=goalId),
            )


            return {
                "goals": goalsPayload,
                "operators": operatorsPayload,
                "participants": participantsPayload,
                "friends": friendsPayload,
                "transactions": transactionsPayload,
            }

        self._run_request_in_thread(
            request_func=request_func,
            on_success=self._apply_goal_payload,
            on_error=self._on_load_error,
        )

    @staticmethod
    def _extract_operators(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            items = payload["data"]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        result: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            operatorId = int(item.get("id") or 0)
            op = str(item.get("goalOperation") or item.get("goalOperator") or "").strip()
            rule = item.get("goalRule")

            try:
                ruleInt = int(rule or 0)
            except Exception:
                ruleInt = 0

            if operatorId > 0 and op:
                result.append({"operatorID": operatorId, "goalOperator": op, "goalRule": ruleInt})

        return result



    def _apply_goal_payload(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, dict):
            self.statusText = "Некорректный ответ"
            return

        if not (self.goalNameText or "").strip():
            resolvedName = self._resolve_goal_name_from_goals(payload.get("goals"), int(self.goalId))
            if resolvedName:
                self.goalNameText = resolvedName

        self.titleText = f"Моя Цель: {self.goalNameText}" if self.goalNameText else "Моя цель"
        self.statusText = ""

        operators = self._extract_operators(payload.get("operators"))
        self._operatorsCache = operators
        self._originalOperators = [dict(x) for x in operators]

        self.conditionsData = self._build_conditions_rv_data(operators)

        participants = self._extract_participants(payload.get("participants"))
        self._participantsCache = participants
        self._originalParticipantIds = {int(x.get("id") or 0) for x in participants if int(x.get("id") or 0) > 0}

        self.participantsData = self._build_participants_rv_data(participants)

        friends = self._extract_friends(payload.get("friends"))
        self._friendsCache = friends

        transactionsPayload = payload.get("transactions")
        transactions: list[dict[str, Any]] = []

        if isinstance(transactionsPayload, dict):
            if isinstance(transactionsPayload.get("transactions"), list):
                transactions = [x for x in transactionsPayload["transactions"] if isinstance(x, dict)]
            elif isinstance(transactionsPayload.get("data"), list):
                transactions = [x for x in transactionsPayload["data"] if isinstance(x, dict)]
        elif isinstance(transactionsPayload, list):
            transactions = [x for x in transactionsPayload if isinstance(x, dict)]

        if transactions:
            self.goalTransactionsData = self._build_goal_transactions_rv_data(transactions)


        self._apply_friend_search()

    def _on_load_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки"

    def on_back_button_click(self) -> None:
        if not self.manager:
            return
        if self.manager.has_screen("goals"):
            self.manager.current = "goals"
            return
        if self.manager.has_screen("goals_catalog"):
            self.manager.current = "goals_catalog"
            return
        if self.manager.has_screen("home"):
            self.manager.current = "home"

    def on_save_button_click(self) -> None:
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        if self.goalId <= 0:
            self.statusText = "Не указан goalId."
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password
        goalId = int(self.goalId)

        desiredOperators = self._build_operators_from_conditions_rv()
        desiredParticipantIds = self._build_participant_ids_from_rv()

        toAddParticipants = sorted(list(set(desiredParticipantIds) - set(self._originalParticipantIds)))
        toRemoveParticipants = sorted(list(set(self._originalParticipantIds) - set(desiredParticipantIds)))

        opsToAdd, opsToRemove = self._diff_operators(desiredOperators)

        self.isLoading = True
        self.statusText = "Сохранение..."

        def request_func() -> dict[str, Any]:
            if toAddParticipants:
                payloadAdd = GaolParticipant(
                    goalID=goalId,
                    participants=[ParticipantCatalog(userID=pid) for pid in toAddParticipants],
                )
                self._apiClient.post_goal_participant(userName, password, payloadAdd)

            if toRemoveParticipants:
                payloadDel = GaolParticipant(
                    goalID=goalId,
                    participants=[ParticipantCatalog(userID=pid) for pid in toRemoveParticipants],
                )
                self._apiClient.delete_goal_participant(userName, password, payloadDel)

            removedIds = [x.get("operatorID") for x in opsToRemove if int(x.get("operatorID") or 0) > 0]
            for operatorId in removedIds:
                self._apiClient.delete_goal_operator(userName, password, DeleteGoalOperatorQuery(operatorID=int(operatorId)))

            if opsToAdd:
                payloads = [
                    PostGoalOperatorsPayload(goalOperator=str(x["goalOperator"]), goalRule=int(x["goalRule"]))
                    for x in opsToAdd
                ]
                self._apiClient.post_goal_operators(userName, password, PostGoalOperatorsQuery(goalID=goalId), payloads)

            return {"ok": True}

        def on_success(_: Any) -> None:
            self.isLoading = False
            self.statusText = "Сохранено."

            self._originalParticipantIds = set(desiredParticipantIds)
            self._originalOperators = [dict(x) for x in desiredOperators]

        def on_error(statusCode: Optional[int], errorPayload: Any) -> None:
            self.isLoading = False
            detail = ""
            if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
                detail = errorPayload["detail"].strip()
            self.statusText = f"Ошибка сохранения: {detail}" if detail else "Ошибка сохранения"

        self._run_request_in_thread(
            request_func=request_func,
            on_success=on_success,
            on_error=on_error,
        )

    def on_delete_button_click(self) -> None:
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        if self.goalId <= 0:
            self.statusText = "Не указан goalId."
            return

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password
        goalId = int(self.goalId)

        self.isLoading = True
        self.statusText = "Удаление..."

        def request_func() -> Any:
            return self._apiClient.delete_goal(userName, password, DeleteGoalQuery(goalID=goalId))

        def on_success(_: Any) -> None:
            self.isLoading = False
            self.statusText = "Цель удалена."
            self.on_back_button_click()

        def on_error(statusCode: Optional[int], errorPayload: Any) -> None:
            self.isLoading = False
            detail = ""
            if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
                detail = errorPayload["detail"].strip()
            self.statusText = f"Ошибка удаления: {detail}" if detail else "Ошибка удаления"

        self._run_request_in_thread(
            request_func=request_func,
            on_success=on_success,
            on_error=on_error,
        )

    def on_add_condition_button_click(self) -> None:
        nextIndex = len(self.conditionsData)
        self.conditionsData = list(self.conditionsData) + [
            {"screen": self, "index": nextIndex, "operatorId": 0, "operatorValue": ">=", "valueText": ""}
        ]

    def on_delete_condition_click(self, index: int) -> None:
        updated = [c for c in self.conditionsData if int(c.get("index") or -1) != int(index)]
        for i, item in enumerate(updated):
            item["index"] = i
            item["screen"] = self
        self.conditionsData = updated

    def on_condition_operator_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self.conditionsData):
            self.conditionsData[index]["operatorValue"] = value

    def on_condition_value_change(self, index: int, value: str) -> None:
        if 0 <= index < len(self.conditionsData):
            self.conditionsData[index]["valueText"] = value

    def on_open_friend_popup_click(self) -> None:
        self.selectedFriendId = 0
        self.selectedFriendName = ""
        self.friendSearchText = ""
        self._apply_friend_search()

        if self._friendsPopup is None:
            popupContent = FriendPickPopupContent(screen=self)
            self._friendsPopup = Popup(
                title="",
                content=popupContent,
                auto_dismiss=True,
                size_hint=(0.92, 0.62),
                separator_height=0,
            )
        else:
            self._friendsPopup.content.screen = self

        self._friendsPopup.open()

    def close_friend_popup(self) -> None:
        if self._friendsPopup is not None:
            self._friendsPopup.dismiss()

    def on_friend_pick_click(self, friendId: int, friendName: str) -> None:
        self.selectedFriendId = int(friendId)
        self.selectedFriendName = str(friendName)
        self._apply_friend_search()

    def on_friend_search_button_click(self) -> None:
        query = ""
        if "friendSearchInput" in self.ids:
            query = str(self.ids.friendSearchInput.text or "").strip()
        else:
            query = str(self.friendSearchText or "").strip()
        self.friendSearchText = query
        self._apply_friend_search()

    def on_confirm_add_friend_click(self) -> None:
        if self.selectedFriendId <= 0:
            return

        existingIds = {int(p.get("participantId") or 0) for p in self.participantsData}
        if self.selectedFriendId not in existingIds:
            self.participantsData = list(self.participantsData) + [
                {"screen": self, "participantId": self.selectedFriendId, "userName": self.selectedFriendName}
            ]

        self.close_friend_popup()

    def on_remove_participant_click(self, participantId: int) -> None:
        self.participantsData = [
            p for p in self.participantsData if int(p.get("participantId") or 0) != int(participantId)
        ]

    @staticmethod
    def _resolve_goal_name_from_goals(goalsPayload: Any, goalId: int) -> str:
        goalsList: list[dict[str, Any]] = []
        if isinstance(goalsPayload, list):
            goalsList = [x for x in goalsPayload if isinstance(x, dict)]
        elif isinstance(goalsPayload, dict) and isinstance(goalsPayload.get("data"), list):
            goalsList = [x for x in goalsPayload["data"] if isinstance(x, dict)]

        for g in goalsList:
            if int(g.get("id") or 0) == int(goalId):
                return str(g.get("goalName") or "").strip()
        return ""

    @staticmethod
    def _extract_participants(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            items = payload["data"]
        else:
            items = []

        result: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pid = int(item.get("id") or item.get("userID") or 0)
            name = str(item.get("userName") or "").strip()
            if pid > 0 and name:
                result.append({"id": pid, "userName": name})
        return result

    @staticmethod
    def _extract_friends(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            items = payload["data"]
        else:
            items = []

        result: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            fid = int(item.get("id") or 0)
            name = str(item.get("userName") or "").strip()
            if fid > 0 and name:
                result.append({"id": fid, "userName": name})

        return result

    @staticmethod
    def _extract_operators_from_goal_transactions(payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            return []

        ruleScores = metadata.get("ruleScores")
        if not isinstance(ruleScores, list):
            return []

        result: list[dict[str, Any]] = []
        for item in ruleScores:
            if not isinstance(item, dict):
                continue

            op = str(item.get("goalOperation") or item.get("goalOperator") or "").strip()
            rule = item.get("goalRule")

            try:
                ruleInt = int(rule or 0)
            except Exception:
                ruleInt = 0

            operatorId = int(item.get("operatorID") or item.get("id") or item.get("operatorId") or 0)

            if op:
                result.append({"operatorID": operatorId, "goalOperator": op, "goalRule": ruleInt})

        return result

    def _build_conditions_rv_data(self, operators: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for i, item in enumerate(operators):
            data.append(
                {
                    "screen": self,
                    "index": i,
                    "operatorId": int(item.get("operatorID") or 0),
                    "operatorValue": str(item.get("goalOperator") or ">="),
                    "valueText": str(item.get("goalRule") or ""),
                }
            )
        return data

    def _build_participants_rv_data(self, participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for item in participants:
            pid = int(item.get("id") or 0)
            name = str(item.get("userName") or "").strip()
            if pid > 0 and name:
                data.append({"screen": self, "participantId": pid, "userName": name})
        return data

    def _apply_friend_search(self) -> None:
        queryValue = (self.friendSearchText or "").strip().lower()

        def _extract_friend_name(item: dict[str, Any]) -> str:
            candidateKeys = ("nickname", "userName", "login", "name", "title")
            for key in candidateKeys:
                value = item.get(key)
                if value is not None:
                    nameValue = str(value).strip()
                    if nameValue:
                        return nameValue
            return ""

        friends = list(self._friendsCache)

        if queryValue:
            friends = [
                f for f in friends
                if queryValue in _extract_friend_name(f).lower()
            ]

        data: list[dict[str, Any]] = []
        for item in friends:
            try:
                friendIdValue = int(item.get("id") or 0)
            except (TypeError, ValueError):
                friendIdValue = 0

            friendNameValue = _extract_friend_name(item)

            if friendIdValue <= 0 or not friendNameValue:
                continue

            data.append(
                {
                    "screen": self,
                    "friendId": friendIdValue,
                    "friendName": friendNameValue,
                    "isSelected": friendIdValue == self.selectedFriendId,
                }
            )

        self.friendsData = data


    def _build_participant_ids_from_rv(self) -> list[int]:
        ids: list[int] = []
        for p in self.participantsData:
            pid = int(p.get("participantId") or 0)
            if pid > 0 and pid not in ids:
                ids.append(pid)
        return ids

    def _build_operators_from_conditions_rv(self) -> list[dict[str, Any]]:
        operatorMap = {"=": "=="}

        result: list[dict[str, Any]] = []
        for item in self.conditionsData:
            opRaw = str(item.get("operatorValue") or "").strip()
            op = operatorMap.get(opRaw, opRaw)

            rawValue = str(item.get("valueText") or "").strip()
            try:
                rule = int(float(rawValue.replace(",", "."))) if rawValue else 0
            except Exception:
                rule = 0

            operatorId = int(item.get("operatorId") or 0)
            if op:
                result.append({"operatorID": operatorId, "goalOperator": op, "goalRule": rule})
        return result

    def _diff_operators(
        self,
        desired: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:

        originalById = {
            int(x["operatorID"]): x
            for x in self._originalOperators
            if int(x.get("operatorID", 0)) > 0
        }

        desiredById = {
            int(x["operatorID"]): x
            for x in desired
            if int(x.get("operatorID", 0)) > 0
        }

        toAdd: list[dict[str, Any]] = []
        toRemove: list[dict[str, Any]] = []

        for operatorId, original in originalById.items():
            current = desiredById.get(operatorId)

            if current is None:
                toRemove.append(original)
                continue

            if (
                str(original.get("goalOperator")) != str(current.get("goalOperator"))
                or int(original.get("goalRule")) != int(current.get("goalRule"))
            ):
                toRemove.append(original)
                toAdd.append({
                    "operatorID": 0,
                    "goalOperator": current["goalOperator"],
                    "goalRule": current["goalRule"],
                })

        for item in desired:
            if int(item.get("operatorID", 0)) == 0:
                toAdd.append(item)

        return toAdd, toRemove

    def _run_request_in_thread(self, request_func, on_success, on_error) -> None:
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
