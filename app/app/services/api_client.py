import requests
from typing import Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from .schema import *

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

    # Users
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
    
    def get_users(self, userName: str, password: str, query:GetUsersQuery) -> Dict:
        url = f"{self._apiConfig.baseUrl}/user" + query.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.get(url,headers=headers,timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response
    
    def update_users(self, userName: str, password: str, payload:UpdateUser) -> Dict:
        url = f"{self._apiConfig.baseUrl}/user"  
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.patch(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response
    
    def delete_users(self, userName: str, password: str) -> Dict:
        url = f"{self._apiConfig.baseUrl}/user"  
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.delete(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response
    
    # Bank transactions
    def get_bank_transactions(self, userName: str, password: str, query:GetBankTransactionsQuery) -> List[Dict[str,Any]]:
        url = f"{self._apiConfig.baseUrl}/bank_transactions" + query.to_query()  
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.get(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response
    
    def post_bank_transactions(self, userName: str, password: str, query:PostBankTransactionsQuery, payload:PostBankTransactionsManualLoadPayload) -> Dict[str,Any]:
        url = f"{self._apiConfig.baseUrl}/bank_transactions" + query.to_query()  
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.post(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response
        
    def patch_bank_transactions(self, userName: str, password: str, query:PatchBankTransactionsQuery, payload:PatchBankTransactionsManualLoadPayload) -> Dict[str,Any]:
        url = f"{self._apiConfig.baseUrl}/bank_transactions" + query.to_query()  
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.patch(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response
    
    def delete_bank_transactions(self, userName: str, password: str, query:DeleteBankTransactionsQuery) -> Dict[str,Any]:
        url = f"{self._apiConfig.baseUrl}/bank_transactions" + query.to_query()  
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.delete(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def post_bank_transactions_by_file(self, userName:str, password:str, filePath:str, query:PostBankTransactionsQuery) -> Dict[str,Any]:
        url = f"{self._apiConfig.baseUrl}/bank_transactions/file" + query.to_query()  
        headers = {"X-Username": userName,"X-Password": password}
        
        with open(filePath, "rb") as f:
            files = {"file": f}
            response = requests.post(url, files=files, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response


    # Friends
    def get_friends(self, userName: str, password: str) -> Dict:
        url = f"{self._apiConfig.baseUrl}/friend"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.get(url,headers=headers,timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def post_friends(self, userName: str, password: str, payload:PostFriendPayload) -> Dict:
        url = f"{self._apiConfig.baseUrl}/friend"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.post(url,json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def delete_friends(self, userName: str, password: str, payload:DeleteFriendPayload) -> Dict:
        url = f"{self._apiConfig.baseUrl}/friend"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.delete(url,json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    # Goals
    def post_goal(self, userName: str, password: str, payload:AddGoalPayload) -> Dict:
        url = f"{self._apiConfig.baseUrl}/goals"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.post(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def delete_goal(self, userName: str, password: str, query:DeleteGoalQuery) -> Dict:
        url = f"{self._apiConfig.baseUrl}/goals" + query.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.delete(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def post_goal_participant(self, userName: str, password: str, payload:GaolParticipant) -> Dict:
        url = f"{self._apiConfig.baseUrl}/goals/participant"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.post(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def delete_goal_participant(self, userName: str, password: str, payload:GaolParticipant) -> Dict:
        url = f"{self._apiConfig.baseUrl}/goals/participant"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.delete(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def post_goal_operators(self, userName: str, password: str, query:PostGoalOperatorsQuery, payloads:List[PostGoalOperatorsPayload]) -> Dict:
        url = f"{self._apiConfig.baseUrl}/goals/operators" + query.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.post(url, json=[payload.to_dict() for payload in payloads], headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def delete_goal_operator(self, userName: str, password: str, query:PostGoalOperatorsQuery) -> Dict:
        url = f"{self._apiConfig.baseUrl}/goals/operators" + query.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.delete(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def get_goal(self, userName: str, password: str) -> Dict:
        url = f"{self._apiConfig.baseUrl}/goals"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.get(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    # Category
    def get_category(self, userName: str, password: str) -> Dict:
        url = f"{self._apiConfig.baseUrl}/category"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.get(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def post_category(self, userName: str, password:str, payload:AddCategoryPayload) -> Dict:
        url = f"{self._apiConfig.baseUrl}/category"
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.post(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def delete_category(self, userName: str, password:str, qeury:DeleteCategoryQuery) -> Dict:
        url = f"{self._apiConfig.baseUrl}/category" + qeury.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.delete(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def patch_category(self, userName: str, password:str, qeury:PatchCategoryQuery, payload:UpdateDataServiceSchemaPayLoad) -> Dict:
        url = f"{self._apiConfig.baseUrl}/category" + qeury.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.patch(url, json=payload.to_dict(), headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def get_category_transactions(self, userName: str, password:str, qeury:GetCategoryTransactionsQeury) -> Dict:
        url = f"{self._apiConfig.baseUrl}/category/transactions" + qeury.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.get(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response


    # Analytics
    def _get_analytics(self, userName: str, password:str, url) -> Dict:
        # url = f"{self._apiConfig.baseUrl}/category/transactions" + qeury.to_query()
        headers = {"X-Username": userName,"X-Password": password}
        response = requests.get(url, headers=headers, timeout=self._apiConfig.timeoutSeconds)
        response.raise_for_status()
        contentType = response.headers.get("content-type", "")
        if "application/json" in contentType:
            return response.json()
        return response

    def get_analytics_balans(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/balans"
        return self._get_analytics(userName, password, url)

    def get_analytics_cash_flow(self, userName: str, password:str, query:GetAnalyticsCashFlow):
        url = f"{self._apiConfig.baseUrl}/ananlytics/cash_flow" + query.to_query()
        return self._get_analytics(userName, password, url)

    def get_analytics_expense_category_distribution(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/expense_category_distribution"
        return self._get_analytics(userName, password, url)

    def get_analytics_income_category_distribution(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/income_category_distribution"
        return self._get_analytics(userName, password, url)

    def get_analytics_last_transactions(self, userName: str, password:str, query:GetAnalyticsLastTransactions):
        url = f"{self._apiConfig.baseUrl}/ananlytics/last_transactions" + query.to_query()
        return self._get_analytics(userName, password, url)

    def get_analytics_anomaly_transactions(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/anomaly_transactions"
        return self._get_analytics(userName, password, url)

    def get_analytics_habits_cost(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/habits_cost"
        return self._get_analytics(userName, password, url)
    
    def get_analytics_user_financial_profile(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/user_financial_profile"
        return self._get_analytics(userName, password, url)

    def get_analytics_financial_health_score(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/financial_health_score"
        return self._get_analytics(userName, password, url)

    def get_analytics_predict_next_month_expenses(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/predict_next_month_expenses"
        return self._get_analytics(userName, password, url)

    def get_analytics_predict_category_expenses(self, userName: str, password:str):
        url = f"{self._apiConfig.baseUrl}/ananlytics/predict_category_expenses"
        return self._get_analytics(userName, password, url)

