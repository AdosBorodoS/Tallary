from __future__ import annotations

import json
import os
from dataclasses import dataclass
from threading import Lock
from typing import Optional


@dataclass
class SessionData:
    userName: str = ""
    password: str = ""
    isAuthorized: bool = False


class SessionService:
    def __init__(self, storagePath: Optional[str] = None) -> None:
        self._lock = Lock()
        self._sessionData = SessionData()
        self._storagePath = storagePath

    def set_credentials(self, userName: str, password: str, isAuthorized: bool) -> None:
        with self._lock:
            self._sessionData.userName = userName
            self._sessionData.password = password
            self._sessionData.isAuthorized = isAuthorized

        self._try_persist()

    def clear(self) -> None:
        with self._lock:
            self._sessionData = SessionData()

        self._try_persist()

    def get_user_name(self) -> str:
        with self._lock:
            return self._sessionData.userName

    def is_authorized(self) -> bool:
        with self._lock:
            return self._sessionData.isAuthorized

    def get_auth_headers(self) -> dict:
        """
        Заголовки под твой Swagger:
          X-Username: <userName>
          X-Password: <password>
        """
        with self._lock:
            if not self._sessionData.userName or not self._sessionData.password:
                return {}
            return {
                "X-Username": self._sessionData.userName,
                "X-Password": self._sessionData.password,
            }

    def load(self) -> None:
        """
        Поднимает сессию из файла (если storagePath задан).
        """
        if not self._storagePath:
            return
        if not os.path.exists(self._storagePath):
            return

        try:
            with open(self._storagePath, "r", encoding="utf-8") as file:
                payload = json.load(file)

            userName = str(payload.get("userName", "")).strip()
            password = str(payload.get("password", "")).strip()
            isAuthorized = bool(payload.get("isAuthorized", False))

            with self._lock:
                self._sessionData = SessionData(
                    userName=userName,
                    password=password,
                    isAuthorized=isAuthorized
                )
        except Exception:
            # Не валим приложение из-за битого файла
            with self._lock:
                self._sessionData = SessionData()

    def _try_persist(self) -> None:
        if not self._storagePath:
            return

        try:
            os.makedirs(os.path.dirname(self._storagePath), exist_ok=True)
            with self._lock:
                payload = {
                    "userName": self._sessionData.userName,
                    "password": self._sessionData.password,
                    "isAuthorized": self._sessionData.isAuthorized,
                }

            with open(self._storagePath, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
        except Exception:
            # Игнорируем ошибки сохранения, чтобы не ломать UX
            pass
