from __future__ import annotations

from kivy.properties import ListProperty
from kivy.uix.screenmanager import Screen


class TransactionsUploadScreen(Screen):
    # Заглушка под будущий API: список последних файлов
    recentFilesRvData = ListProperty([])

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        # TODO: заменить на вызов API "recent uploads"
        self.recentFilesRvData = [
            {
                "fileName": "СберБанк_Выписка_2023.ofx",
                "dateText": "23 мая 2024, 14:30",
                "statusText": "Успешно",
                "countText": "+125 транзакций",
            },
            {
                "fileName": "ВТБ_Кредитка_Мар_2024.csv",
                "dateText": "20 мая 2024, 11:00",
                "statusText": "Успешно",
                "countText": "+88 транзакций",
            },
        ]

    def on_back_click(self) -> None:
        if self.manager:
            self.manager.current = "transactions"

    def on_manual_upload_click(self) -> None:
        if self.manager:
            self.manager.current = "manual_transaction"

    def on_bank_click(self, bank_slug: str) -> None:
        print(f"TODO: bank click => {bank_slug} (подключение/инструкции/импорт)")
