import threading
from typing import Any, Callable, Optional

import requests
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

from ..services.api_client import ApiClient
from ..services.session_service import SessionService


class LoginScreen(Screen):
    statusText = StringProperty("")

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

    def on_login_button_click(self) -> None:
        userName, password = self._get_credentials()
        if not userName or not password:
            self._set_status("Введите логин и пароль")
            return

        self._set_status("Авторизация...")
        self._run_request_in_thread(
            request_func=lambda: self._apiClient.authorize_user(userName=userName, password=password),
            on_success=lambda result: self._on_auth_success(userName=userName, password=password, result=result),
            on_error=self._handle_login_error
        )

    def on_register_button_click(self) -> None:
        userName, password = self._get_credentials()
        if not userName or not password:
            self._set_status("Введите логин и пароль")
            return

        self._set_status("Регистрация...")
        self._run_request_in_thread(
            request_func=lambda: self._apiClient.register_user(userName=userName, password=password),
            on_success=lambda result: self._on_register_success(userName=userName, password=password, result=result),
            on_error=self._handle_register_error
        )

    def toggle_password_visibility(self) -> None:
        self.isPasswordHidden = not self.isPasswordHidden
        passwordInput = self.ids.passwordInput
        passwordInput.password = self.isPasswordHidden

        if hasattr(passwordInput, "icon_right"):
            passwordInput.icon_right = "eye-off-outline" if self.isPasswordHidden else "eye-outline"

    def _on_auth_success(self, userName: str, password: str, result: Any) -> None:
        if not self._is_auth_response_ok(result=result, expectedUserName=userName):
            self._set_status("Неверный логин или пароль")
            return

        self._sessionService.set_credentials(userName=userName, password=password, isAuthorized=True)
        self._set_status("Успешная авторизация")
        self.manager.current = "home"

        # self.manager.current = "home"  # когда добавишь следующий экран

    def _on_register_success(self, userName: str, password: str, result: Any) -> None:
        self._sessionService.set_credentials(userName=userName, password=password, isAuthorized=True)
        self._set_status("Успешная регистрация")
        self.manager.current = "home"

        # self.manager.current = "home"

    def _handle_register_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        if statusCode == 409:
            # FastAPI обычно возвращает {"detail":"Username already exist"}
            detailText = self._extract_detail_text(errorPayload=errorPayload) or "Логин уже существует"
            self._set_status(detailText)
            return

        detailText = self._extract_detail_text(errorPayload=errorPayload)
        if detailText:
            self._set_status(f"Ошибка регистрации: {detailText}")
        else:
            self._set_status(f"Ошибка регистрации: HTTP {statusCode}")

    def _handle_login_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        # Варианты: 401 / 403 и т.д. — зависит от твоего backend
        if statusCode in (401, 403):
            self._set_status("Неверный логин или пароль")
            return

        detailText = self._extract_detail_text(errorPayload=errorPayload)
        if detailText:
            self._set_status(f"Ошибка авторизации: {detailText}")
        else:
            self._set_status(f"Ошибка авторизации: HTTP {statusCode}")

    def _run_request_in_thread(
        self,
        request_func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Optional[int], Any], None]
    ) -> None:
        def worker() -> None:
            try:
                result = request_func()
                Clock.schedule_once(lambda _: on_success(result), 0)
                return

            except requests.HTTPError as ex:
                response = ex.response
                statusCode = response.status_code if response is not None else None
                errorPayload = self._safe_extract_response_payload(response=response)
                Clock.schedule_once(lambda _: on_error(statusCode, errorPayload), 0)
                return

            except Exception as ex:
                Clock.schedule_once(lambda _: on_error(None, {"detail": str(ex)}), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _get_credentials(self) -> tuple[str, str]:
        userName = (self.ids.userNameInput.text or "").strip()
        password = (self.ids.passwordInput.text or "").strip()
        return userName, password

    def _set_status(self, text: str) -> None:
        self.statusText = text

    def _safe_extract_response_payload(self, response: Optional[requests.Response]) -> Any:
        if response is None:
            return {"detail": "No response"}

        try:
            # FastAPI error body часто JSON
            return response.json()
        except Exception:
            # Иногда plain text
            textValue = (response.text or "").strip()
            return {"detail": textValue} if textValue else {"detail": f"HTTP {response.status_code}"}

    def _extract_detail_text(self, errorPayload: Any) -> str:
        if isinstance(errorPayload, dict):
            detailValue = errorPayload.get("detail")
            if isinstance(detailValue, str):
                return detailValue.strip()
            return ""
        if isinstance(errorPayload, str):
            return errorPayload.strip()
        return ""

    def _is_auth_response_ok(self, result: Any, expectedUserName: str) -> bool:
        """
        Считаем успешной авторизацию, если backend вернул data и там есть пользователь expectedUserName.
        """
        if not isinstance(result, dict):
            return False

        dataValue = result.get("data")
        if not isinstance(dataValue, list) or len(dataValue) == 0:
            return False

        firstItem = dataValue[0]
        if not isinstance(firstItem, dict):
            return False

        return str(firstItem.get("userName", "")).strip() == expectedUserName
