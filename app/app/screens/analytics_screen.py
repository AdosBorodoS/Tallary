from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService
from app.widgets.bottom_nav_mixin import BottomNavMixin
from app.widgets.donut_chart_widget import DonutChartWidget
from app.services.schema import GetAnalyticsCashFlow, GetAnalyticsLastTransactions


class AnalyticsScreen(BottomNavMixin, Screen):
    mode = StringProperty("expense")

    isLoading = BooleanProperty(False)
    statusText = StringProperty("")

    balanceText = StringProperty("— ₽")
    literacyText = StringProperty("—/100")

    totalOpsText = StringProperty("—")
    categoriesCountText = StringProperty("—")

    pieMetaText = StringProperty("— ₽ • — категорий")

    anomalyTitleText = StringProperty("Нет данных")
    anomalyDescText = StringProperty("")
    anomalyAmountText = StringProperty("")

    habitCostText = StringProperty("— ₽")

    profileSummaryText = StringProperty("—")
    profileMetaText = StringProperty("")
    profileRecsText = StringProperty("")

    forecastAmountText = StringProperty("— ₽")
    forecastMetaText = StringProperty("")

    forecastCatRvData = ListProperty([])
    forecastCatMetaText = StringProperty("")

    pieRvData = ListProperty([])
    flowRvData = ListProperty([])

    _isLoadedOnce = False
    _cachedAllPayload = None
    _cachedExpensePie = None
    _cachedIncomePie = None

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)

        if not self._isLoadedOnce:
            self._load_all()

    # ---------- UI ----------
    def set_mode(self, mode: str) -> None:
        normalizedMode = (mode or "").strip().lower()
        if normalizedMode not in ("expense", "income"):
            return

        if self.mode == normalizedMode:
            return

        self.mode = normalizedMode

        if not getattr(self, "_isLoadedOnce", False) and getattr(self, "isLoading", False):
            self.statusText = "Загрузка аналитики..."
            self._apply_pie_from_cache()
            return

        self._apply_pie_from_cache()

    def _apply_pie_from_cache(self) -> None:
        if self.mode == "expense":
            piePayload = self._cachedExpensePie
        else:
            piePayload = self._cachedIncomePie

        if piePayload is None:
            self.pieRvData = []
            self.pieMetaText = "Данные загружаются..." if self.isLoading else "Нет данных"
            try:
                chart = self.ids.get("pieChart")
                if chart is not None:
                    chart.set_slices([])
            except Exception:
                pass
            return

        self._apply_pie(piePayload)

    def on_refresh_click(self) -> None:
        self._load_all(force=True)


    def on_refresh_click(self) -> None:
        if self.isLoading:
            return

        self._isLoadedOnce = False
        self._cachedAllPayload = None
        self._cachedExpensePie = None
        self._cachedIncomePie = None

        self._load_all(force=True)

    # ---------- Loading orchestration ----------
    def _load_all(self, force: bool = False) -> None:
        if self._isLoadedOnce and not force:
            return

        if self.isLoading and not force:
            return

        self.isLoading = True
        self.statusText = "Загрузка аналитики..."
        self._run_request_in_thread(
            request_func=self._fetch_all_from_api,
            on_success=self._apply_all,
            on_error=self._handle_error,
        )


    def _load_pie_only(self) -> None:
        self._run_request_in_thread(
            request_func=self._fetch_pie_from_api,
            on_success=self._apply_pie,
            on_error=self._handle_error,
        )

    def _fetch_all_from_api(self) -> dict:
        if not self._sessionService.is_authorized():
            raise Exception("Сессия не найдена. Авторизуйтесь.")

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        payload: dict[str, Any] = {}

        payload["balance"] = self._apiClient.get_analytics_balans(userName, password)

        payload["flow"] = self._apiClient.get_analytics_cash_flow(
            userName,
            password,
            GetAnalyticsCashFlow(period="month"),
        )

        payload["pie_expense"] = self._apiClient.get_analytics_expense_category_distribution(userName, password)
        payload["pie_income"] = self._apiClient.get_analytics_income_category_distribution(userName, password)

        payload["anomaly"] = self._apiClient.get_analytics_anomaly_transactions(userName, password)

        payload["habit_cost"] = self._apiClient.get_analytics_habits_cost(userName, password)

        payload["profile"] = self._apiClient.get_analytics_user_financial_profile(userName, password)

        payload["literacy"] = self._apiClient.get_analytics_financial_health_score(userName, password)

        payload["forecast"] = self._apiClient.get_analytics_predict_next_month_expenses(userName, password)
        payload["forecast_by_category"] = self._apiClient.get_analytics_predict_category_expenses(userName, password)

        return payload


    def _fetch_pie_from_api(self) -> Any:
        if not self._sessionService.is_authorized():
            raise Exception("Сессия не найдена. Авторизуйтесь.")

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        if self.mode == "expense":
            return self._apiClient.get_analytics_expense_category_distribution(userName, password)

        return self._apiClient.get_analytics_income_category_distribution(userName, password)

    def _apply_all(self, payload: Any) -> None:
        self.isLoading = False
        self.statusText = ""

        if not isinstance(payload, dict):
            self.statusText = "Некорректный ответ аналитики"
            return

        self._apply_balance(payload.get("balance"))
        self._apply_flow(payload.get("flow"))
        self._apply_pie(payload.get("pie_expense") if self.mode == "expense" else payload.get("pie_income"))
        self._apply_anomaly(payload.get("anomaly"))
        self._apply_habit_cost(payload.get("habit_cost"))
        self._apply_profile(payload.get("profile"))
        self._apply_literacy(payload.get("literacy"))
        self._apply_forecast(payload.get("forecast"))
        self._apply_forecast_by_category(payload.get("forecast_by_category"))

        self._cachedAllPayload = payload
        self._cachedExpensePie = payload.get("pie_expense")
        self._cachedIncomePie = payload.get("pie_income")
        self._isLoadedOnce = True

        self.statusText = ""

        self._apply_pie_from_cache()


    def _apply_forecast_by_category(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self.forecastCatRvData = []
            self.forecastCatMetaText = ""
            return

        by_cat = payload.get("forecastByCategory")
        total = payload.get("totalForecast")
        confidence = str(payload.get("confidence") or "").strip()
        msg = str(payload.get("message") or "").strip()

        rows = []
        if isinstance(by_cat, dict):
            items = []
            for k, v in by_cat.items():
                if isinstance(k, str):
                    items.append((k, v))
            items.sort(key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0.0, reverse=True)

            palette = [
                (0.27, 0.62, 0.97, 1),
                (0.20, 0.80, 0.55, 1),
                (0.95, 0.55, 0.20, 1),
                (0.75, 0.35, 0.95, 1),
                (0.95, 0.20, 0.45, 1),
                (0.65, 0.65, 0.65, 1),
            ]

            for idx, (name, amount) in enumerate(items):
                rows.append(
                    {
                        "titleText": name,
                        "percentText": "",
                        "amountText": self._fmt_money(amount),
                        "dotColor": palette[idx % len(palette)],
                    }
                )

        self.forecastCatRvData = rows

        total_s = self._fmt_money(total)
        conf_s = confidence or "—"
        self.forecastCatMetaText = f"Итого: {total_s} • Уверенность: {conf_s}\n{msg}".strip()

    def _apply_balance(self, payload: Any) -> None:
        val = None
        counter = None

        if isinstance(payload, dict):
            val = payload.get("data")
            counter = payload.get("counterOperations")

        self.balanceText = self._fmt_money(val)

        if isinstance(counter, int):
            self.totalOpsText = str(counter)
        else:
            self.totalOpsText = "—"

    def _apply_literacy(self, payload: Any) -> None:
        score = None
        cat = ""
        if isinstance(payload, dict):
            score = payload.get("score")
            cat = str(payload.get("category") or "").strip()
        if isinstance(score, (int, float)):
            self.literacyText = f"{int(score)}/100"
        else:
            self.literacyText = "—/100"
        if cat:
            self.literacyText = f"{self.literacyText} • {cat}"

    def _apply_flow(self, payload: Any) -> None:
        if not isinstance(payload, list):
            self.flowRvData = []
            return

        rows = []
        net_values = []
        for x in payload:
            if isinstance(x, dict) and isinstance(x.get("net"), (int, float)):
                net_values.append(abs(float(x["net"])))
        max_v = max(net_values) if net_values else 1.0

        for x in payload:
            if not isinstance(x, dict):
                continue
            period = str(x.get("period") or "").strip()
            net = x.get("net")
            ratio = 0.0
            if isinstance(net, (int, float)):
                ratio = min(abs(float(net)) / max_v, 1.0)
            rows.append(
                {
                    "periodText": period[-2:] if len(period) >= 2 else period,
                    "valueText": f"net: {self._fmt_money(net)}",
                    "ratio": ratio,
                }
            )

        self.flowRvData = rows

    def _apply_pie(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self.pieRvData = []
            self.pieMetaText = "— ₽ • — категорий"
            return

        data = payload.get("data")
        meta = payload.get("meta")

        total = None
        cats = None
        if isinstance(meta, dict):
            total = meta.get("totalExpense") if self.mode == "expense" else meta.get("totalIncome")
            cats = meta.get("categories")

        if isinstance(cats, int):
            self.categoriesCountText = str(cats)
        else:
            self.categoriesCountText = "—"


        self.pieMetaText = f"{self._fmt_money(total)} • {cats if isinstance(cats, int) else '—'} категорий"

        rows = []
        if isinstance(data, list):
            palette = [
                (0.27, 0.62, 0.97, 1),
                (0.20, 0.80, 0.55, 1),
                (0.95, 0.55, 0.20, 1),
                (0.75, 0.35, 0.95, 1),
                (0.95, 0.20, 0.45, 1),
                (0.65, 0.65, 0.65, 1),
            ]
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                name = str(item.get("category") or "—").strip()
                amount = item.get("amount")
                percent = item.get("percent")
                rows.append(
                    {
                        "titleText": name,
                        "percentText": f"{float(percent):.0f}%" if isinstance(percent, (int, float)) else "—%",
                        "amountText": self._fmt_money(amount),
                        "dotColor": palette[idx % len(palette)],
                    }
                )
        self.pieRvData = rows

        try:
            chart = self.ids.get("pieChart")
            if chart is not None:
                fractions = []

                if isinstance(data, list) and data:
                    hasPercent = any(isinstance(x, dict) and isinstance(x.get("percent"), (int, float)) for x in data)

                    if hasPercent:
                        for item in data:
                            if isinstance(item, dict) and isinstance(item.get("percent"), (int, float)):
                                fractions.append(float(item["percent"]) / 100.0)
                    else:
                        amounts = []
                        for item in data:
                            if isinstance(item, dict) and isinstance(item.get("amount"), (int, float)):
                                amounts.append(max(float(item["amount"]), 0.0))
                        totalAmount = sum(amounts)
                        if totalAmount > 0:
                            for v in amounts:
                                fractions.append(v / totalAmount)

                chart.set_slices(fractions)
        except Exception:
            pass


    def _apply_anomaly(self, payload: Any) -> None:
        if not isinstance(payload, dict) or not payload.get("status"):
            self.anomalyTitleText = "Нет данных"
            self.anomalyDescText = ""
            self.anomalyAmountText = ""
            return

        data = payload.get("data")
        if not isinstance(data, dict):
            return

        category = str(data.get("category") or "Аномалия").strip()
        bank_cat = str(data.get("bankCategory") or "").strip()
        code = str(data.get("code") or "").strip()
        op_date = str(data.get("operationDate") or "").strip()
        post_date = str(data.get("postingDate") or "").strip()
        file_name = str(data.get("fileName") or "").strip()
        desc = str(data.get("description") or "").strip()
        amt = data.get("currencyAmount")

        self.anomalyTitleText = category

        meta_parts = []
        if code:
            meta_parts.append(f"Код: {code}")
        if op_date:
            meta_parts.append(f"Операция: {op_date}")
        if post_date:
            meta_parts.append(f"Проводка: {post_date}")
        if bank_cat and bank_cat != category:
            meta_parts.append(f"Банк: {bank_cat}")
        if file_name:
            meta_parts.append(f"Файл: {file_name}")

        meta = " • ".join(meta_parts)
        desc_short = desc
        if len(desc_short) > 160:
            desc_short = desc_short[:160].rstrip() + "…"

        self.anomalyDescText = (meta + "\n" + desc_short).strip() if meta else desc_short
        self.anomalyAmountText = self._fmt_money(amt)


    def _apply_habit_cost(self, payload: Any) -> None:
        if isinstance(payload, dict) and payload:
            k = next(iter(payload.keys()))
            v = payload.get(k)
            self.habitCostText = f"{k}: {self._fmt_money(v)}"
        else:
            self.habitCostText = "— ₽"

    def _apply_profile(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self.profileSummaryText = "—"
            self.profileMetaText = ""
            self.profileRecsText = ""
            return

        summary = str(payload.get("profileSummary") or "").strip()
        style = str(payload.get("spendingStyle") or "").strip()
        risk = str(payload.get("riskLevel") or "").strip()
        ratio = payload.get("incomeToExpenseRatio")
        top = payload.get("topCategories")
        recs = payload.get("recommendations")

        self.profileSummaryText = summary or "—"

        top_s = ", ".join([str(x) for x in top]) if isinstance(top, list) else ""
        ratio_s = f"{float(ratio):.2f}" if isinstance(ratio, (int, float)) else "—"
        self.profileMetaText = f"Стиль: {style or '—'} • Риск: {risk or '—'} • Доход/расход: {ratio_s}"
        if top_s:
            self.profileMetaText = f"{self.profileMetaText}\nТоп категории: {top_s}"

        if isinstance(recs, list) and recs:
            self.profileRecsText = "Рекомендации:\n- " + "\n- ".join([str(x) for x in recs[:3]])
        else:
            self.profileRecsText = ""

    def _apply_forecast(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self.forecastAmountText = "— ₽"
            self.forecastMetaText = ""
            return

        amount = payload.get("forecastAmount")
        confidence = str(payload.get("confidence") or "").strip()
        msg = str(payload.get("message") or "").strip()
        analyzed = payload.get("periodsAnalyzed")

        self.forecastAmountText = f"{self._fmt_money(amount)}"
        analyzed_s = f"{int(analyzed)}" if isinstance(analyzed, int) else "—"
        conf_s = confidence or "—"
        self.forecastMetaText = f"Уверенность: {conf_s} • Периодов: {analyzed_s}\n{msg}"

    def _handle_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False
        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()
        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки аналитики"

    def _safe_extract_response_payload(self, response: Optional[requests.Response]) -> Any:
        if response is None:
            return {"detail": "No response"}
        try:
            return response.json()
        except Exception:
            textValue = (response.text or "").strip()
            return {"detail": textValue} if textValue else {"detail": f"HTTP {response.status_code}"}

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
                statusCode = response.status_code if response is not None else None
                payload = self._safe_extract_response_payload(response=response)
                Clock.schedule_once(lambda _: on_error(statusCode, payload), 0)
                return
            except Exception as ex:
                Clock.schedule_once(lambda _: on_error(None, {"detail": str(ex)}), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _fmt_money(self, val: Any) -> str:
        if isinstance(val, (int, float)):
            s = f"{val:,.2f}".replace(",", " ")
            if s.endswith(".00"):
                s = s[:-3]
            return f"{s} ₽"
        return "— ₽"
