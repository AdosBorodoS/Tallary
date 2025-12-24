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


class AnalyticsScreen(BottomNavMixin, Screen):
    # режим: expense / income
    mode = StringProperty("expense")

    isLoading = BooleanProperty(False)
    statusText = StringProperty("")

    # summary texts
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

    # RV data
    pieRvData = ListProperty([])
    flowRvData = ListProperty([])

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._load_all()

    # ---------- UI ----------
    def set_mode(self, mode: str) -> None:
        if mode not in ("expense", "income"):
            return
        if self.mode == mode:
            return
        self.mode = mode
        # обновляем только то, что зависит от режима
        self._load_pie_only()

    def on_refresh_click(self) -> None:
        self._load_all(force=True)

    # ---------- Loading orchestration ----------
    def _load_all(self, force: bool = False) -> None:
        if self.isLoading and not force:
            return
        self.isLoading = True
        self.statusText = "Загрузка аналитики..."
        self._run_request_in_thread(
            request_func=self._fetch_all_placeholder,
            on_success=self._apply_all,
            on_error=self._handle_error,
        )

    def _load_pie_only(self) -> None:
        # pie меняется при переключении расход/доход
        self._run_request_in_thread(
            request_func=self._fetch_pie_placeholder,
            on_success=self._apply_pie,
            on_error=self._handle_error,
        )

    # ---------- Placeholder fetchers (TODO: заменить на реальные API вызовы) ----------
    def _fetch_all_placeholder(self) -> dict:
        """
        Собирает все блоки в одном месте (как будто несколько endpoint'ов).
        Потом можно разнести по реальным вызовам.
        """
        payload: dict[str, Any] = {}

        # общий баланс
        payload["balance"] = {"data": 119423.9}

        # поток денег
        payload["flow"] = [
            {"period": "2025-09", "income": 107468, "expense": 0, "net": 107468},
            {"period": "2025-10", "income": 126782.9, "expense": 114827, "net": 11955.9},
        ]

        # пироги
        payload["pie_expense"] = {
            "status": "success",
            "data": [
                {"category": "Прочие операции", "amount": 110257, "percent": 96.02},
                {"category": "Красота", "amount": 3180, "percent": 2.77},
                {"category": "Одежда и обувь", "amount": 890, "percent": 0.78},
                {"category": "Финансовые операции", "amount": 500, "percent": 0.44},
            ],
            "meta": {"totalExpense": 114827, "categories": 4},
        }
        payload["pie_income"] = {
            "status": "success",
            "data": [
                {"category": "Прочие операции", "amount": 185516.9, "percent": 79.2},
                {"category": "За квартиру", "amount": 25234, "percent": 10.77},
                {"category": "комуналка", "amount": 23500, "percent": 10.03},
            ],
            "meta": {"totalIncome": 234250.9, "categories": 3},
        }

        # аномальная транзакция
        payload["anomaly"] = {
            "status": True,
            "data": {
                "id": 52,
                "operationDate": "2025-10-03",
                "category": "Прочие операции",
                "description": "Операция по карте: 220015******7290, RU/MOSCOW/VITA apteka 5266, MCC: 5912",
                "currencyAmount": -12438,
            },
        }

        # цена привычек
        payload["habit_cost"] = {"Прочие операции": 110257}

        # профиль
        payload["profile"] = {
            "profileSummary": "Пользователь тратит значительно меньше, чем зарабатывает. Стиль трат: спонтанный, но осторожный. Уровень финансового риска: низкий.",
            "spendingStyle": "Спонтанный, но осторожный",
            "riskLevel": "низкий",
            "topCategories": ["Прочие операции", "Финансовые операции", "Красота"],
            "incomeToExpenseRatio": 2.04,
            "recommendations": [
                "Уточните категории расходов — это поможет лучше контролировать бюджет.",
                "Множество мелких трат тянут бюджет. Попробуйте недельный лимит на мелочи.",
                "Вы отлично управляете финансами! Подумайте об инвестициях или целях.",
            ],
        }

        # грамотность
        payload["literacy"] = {"score": 47, "category": "Новичок в деньгах"}

        # прогноз
        payload["forecast"] = {
            "forecastAmount": 114827,
            "confidence": "низкая",
            "periodsAnalyzed": 1,
            "message": "Прогноз основан на данных за 1 месяц.",
        }

        payload["forecast_by_category"] = {
            "forecastByCategory": {
                "Прочие операции": 110257,
                "Финансовые операции": 500,
                "Красота": 3180,
                "Одежда и обувь": 890,
            },
            "totalForecast": 114827,
            "confidence": "низкая",
            "message": "Прогноз по 4 категориям. Уровень уверенности: низкая.",
        }


        return payload

    def _fetch_pie_placeholder(self) -> Any:
        # Вытащим из общего placeholder только pie под текущий режим
        all_payload = self._fetch_all_placeholder()
        return all_payload["pie_expense"] if self.mode == "expense" else all_payload["pie_income"]

    # ---------- Apply ----------
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
            # отсортируем по сумме (убывание)
            items = []
            for k, v in by_cat.items():
                if isinstance(k, str):
                    items.append((k, v))
            items.sort(key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0.0, reverse=True)

            # для CategoryStatRow используем amountText, percentText можно сделать "--"
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
                        "percentText": "",  # тут нет percent в ответе
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
        if isinstance(payload, dict):
            val = payload.get("data")
        self.balanceText = self._fmt_money(val)

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
            # можно расширить отдельной строкой, но пока кратко
            self.literacyText = f"{self.literacyText} • {cat}"

    def _apply_flow(self, payload: Any) -> None:
        if not isinstance(payload, list):
            self.flowRvData = []
            return

        # Для UI сделаем бары по abs(net) (как заглушка)
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

        # заглушки по верхним карточкам
        self.totalOpsText = "230"
        self.categoriesCountText = "6"

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
        # коротко, чтобы не раздувать карточку
        desc_short = desc
        if len(desc_short) > 160:
            desc_short = desc_short[:160].rstrip() + "…"

        self.anomalyDescText = (meta + "\n" + desc_short).strip() if meta else desc_short
        self.anomalyAmountText = self._fmt_money(amt)


    def _apply_habit_cost(self, payload: Any) -> None:
        # пример: {"Прочие операции": 110257}
        if isinstance(payload, dict) and payload:
            # возьмём первый ключ как заглушку
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

    # ---------- Error ----------
    def _handle_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False
        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()
        self.statusText = f"Ошибка загрузки: {detail}" if detail else "Ошибка загрузки аналитики"

    # ---------- Thread helper ----------
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

    # ---------- Utils ----------
    def _fmt_money(self, val: Any) -> str:
        if isinstance(val, (int, float)):
            # ₽ и пробелы как в RU — упрощённо
            s = f"{val:,.2f}".replace(",", " ")
            if s.endswith(".00"):
                s = s[:-3]
            return f"{s} ₽"
        return "— ₽"
