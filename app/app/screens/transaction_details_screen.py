from __future__ import annotations

from typing import Any

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
        self._tx = tx

        amount = int(tx.get("amount") or 0)
        self.amountText = self._format_amount_ru(amount)

        self.descriptionText = str(tx.get("title") or "—")
        # bank desc 1/2 — пока рыба: берём title/description2
        self.bankDesc1Text = str(tx.get("title") or "—")
        self.bankDesc2Text = str(tx.get("description2") or "—")

        self.dateText = str(tx.get("date") or "—")
        self.accountText = "Основной счёт"  # TODO: map from API later
        self.selectedCategoryText = str(tx.get("category") or "Прочие операции")

    def on_category_dropdown_click(self) -> None:
        print("Category dropdown clicked (TODO)")

    def on_save_click(self) -> None:
        """
        TODO: тут будет API update (пока рыба).
        """
        print("Save clicked (TODO update transaction)")
        print("TX:", self._tx)
        print("New category:", self.selectedCategoryText)

    def _format_amount_ru(self, amount: int) -> str:
        sign = "" if amount < 0 else ""
        # на экране деталей обычно показывают абсолют и цветом выделяют,
        # но пока оставим знак как в списке:
        sign = "+" if amount > 0 else "−" if amount < 0 else ""
        value = abs(amount)
        formatted = f"{value:,}".replace(",", " ")
        return f"{sign} {formatted} ₽".strip()
