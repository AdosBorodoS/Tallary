from __future__ import annotations

from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen


class ManualTransactionScreen(Screen):
    # dropdown values (заглушки)
    paymentMethods = ListProperty(["Карта", "Наличные", "Перевод", "Онлайн"])
    categories = ListProperty(["Продукты", "Транспорт", "Развлечения", "Прочие операции"])

    # form state (заглушки/черновик)
    dateText = StringProperty("2023-03-15")
    amountText = StringProperty("5000")
    descriptionText = StringProperty("Покупка продуктов")
    categoryText = StringProperty("Продукты")
    isIncome = BooleanProperty(False)
    isAmountValid = BooleanProperty(True)

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self._validate_amount(self.amountText)

    def on_back_click(self) -> None:
        if self.manager:
            self.manager.current = "transactions_upload"

    def on_payment_method_change(self, value: str) -> None:
        # TODO: сохранить способ оплаты
        pass

    def on_date_change(self, value: str) -> None:
        self.dateText = value

    def on_amount_change(self, value: str) -> None:
        self.amountText = value
        self._validate_amount(value)

    def on_description_change(self, value: str) -> None:
        self.descriptionText = value

    def on_category_change(self, value: str) -> None:
        self.categoryText = value

    def set_type(self, is_income: bool) -> None:
        self.isIncome = is_income

    def on_save_click(self) -> None:
        # TODO: отправка на API
        print(
            "SAVE (TODO):",
            {
                "paymentMethod": None,
                "date": self.dateText,
                "amount": self.amountText,
                "type": "income" if self.isIncome else "expense",
                "description": self.descriptionText,
                "category": self.categoryText,
            },
        )

    def _validate_amount(self, value: str) -> None:
        try:
            v = float((value or "").replace(",", "."))
            self.isAmountValid = v > 0
        except Exception:
            self.isAmountValid = False
