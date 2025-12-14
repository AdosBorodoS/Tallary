import requests
from typing import Dict
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass(frozen=True)
class ApiConfig:
    baseUrl: str = "http://localhost:8000" # Поменять на домен хостинга
    timeoutSeconds: int = 10


class AbstractApiClientInterface(ABC):
    
    @abstractmethod
    def register_user(self, userName: str, password: str) -> Dict:
        pass

    @abstractmethod
    def authorize_user(self, userName: str, password: str) -> Dict:
        pass


class ApiClient(AbstractApiClientInterface):
    def __init__(self, apiConfig: ApiConfig):
        self._apiConfig = apiConfig

    def register_user(self, userName: str, password: str) -> Dict:
        url = f"{self._apiConfig.baseUrl}/user"
        payload = {"userName": userName, "password": password}
        response = requests.post(url, json=payload, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        return response

    def authorize_user(self, userName: str, password: str) -> Dict:
        url = f"{self._apiConfig.baseUrl}/login"
        headers = {
            "X-Username": userName,
            "X-Password": password
        }
        response = requests.get(
            url,
            headers=headers,
             timeout=self._apiConfig.timeoutSeconds
         )
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response