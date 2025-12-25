from __future__ import annotations

from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

from app.services.api_client import ApiClient
from app.services.session_service import SessionService


class TransactionDetailsScreen(Screen):
    # read-only displayed
    amountText = StringProperty("— ₽")
    descriptionText = StringProperty("—")
    bankDesc1Text = StringProperty("—")
    bankDesc2Text = StringProperty("—")
    dateText = StringProperty("—")
    accountText = StringProperty("Основной счёт")

    # editable placeholders (future)
    selectedCategoryText = StringProperty("Продукты")  # dropdown later

    # internal
    _tx: dict | None = None

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

    def on_back_click(self) -> None:
        if self.manager:
            self.manager.current = "transactions"

    def set_transaction(self, tx: dict) -> None:
        """
        Приходит normalized dict из TransactionsScreen.
        """
        self._tx = tx or {}

        amount = self._get_amount_value(self._tx)
        self.amountText = self._format_amount_ru(amount)

        self.descriptionText = str(self._tx.get("title") or "—")
        # bank desc 1/2 — пока рыба: берём title/description2
        self.bankDesc1Text = str(self._tx.get("title") or "—")
        self.bankDesc2Text = str(self._tx.get("description2") or "—")

        self.dateText = str(self._tx.get("date") or "—")
        self.accountText = "Основной счёт"  # TODO: map from API later
        self.selectedCategoryText = str(self._tx.get("category") or "Прочие операции")

    def on_category_dropdown_click(self) -> None:
        print("Category dropdown clicked (TODO)")

    def on_save_click(self) -> None:
        """
        TODO: тут будет API update (пока рыба).
        """
        print("Save clicked (TODO update transaction)")
        print("TX:", self._tx)
        print("New category:", self.selectedCategoryText)

    @staticmethod
    def _get_amount_value(tx: dict) -> float:
        """
        Основной источник: currencyAmount.
        Fallback: amount (если вдруг нормализатор положил).
        """
        raw_value = tx.get("currencyAmount")
        if raw_value is None:
            raw_value = tx.get("amount")

        try:
            return float(raw_value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _format_amount_ru(self, amount: float) -> str:
        sign = "+" if amount > 0 else "−" if amount < 0 else ""
        value = abs(amount)

        # если есть копейки — покажем 2 знака, иначе как целое
        if float(value).is_integer():
            as_str = f"{int(value):,}".replace(",", " ")
        else:
            as_str = f"{value:,.2f}".replace(",", " ").replace(".", ",")

        return f"{sign} {as_str} ₽".strip()
