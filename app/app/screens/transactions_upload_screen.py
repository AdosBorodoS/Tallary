from __future__ import annotations

import threading
from typing import Any, Optional

import requests
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


from app.services.api_client import ApiClient
from app.services.schema import PostBankTransactionsQuery, GetUserLoadedFiles
from app.services.session_service import SessionService


class TransactionsUploadScreen(Screen):
    recentFilesRvData = ListProperty([])

    statusText = StringProperty("")
    isLoading = BooleanProperty(False)

    def __init__(self, apiClient: ApiClient, sessionService: SessionService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._apiClient = apiClient
        self._sessionService = sessionService

        self._activeBankSlug: str | None = None
        self._filePickerPopup: Popup | None = None

    def on_pre_enter(self, *args) -> None:
        super().on_pre_enter(*args)
        self.statusText = ""
        self._load_user_files_catalog()

    def _load_user_files_catalog(self) -> None:
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            self.recentFilesRvData = []
            return

        headers = self._sessionService.get_auth_headers()
        userName = headers.get("X-Username", "")
        password = headers.get("X-Password", "")

        query = GetUserLoadedFiles(slugs="alfa,tinkoff")

        self.isLoading = True
        self.statusText = "Загружаю каталог файлов..."

        def worker() -> None:
            try:
                payload = self._apiClient.get_user_files_catalog(
                    userName=userName,
                    password=password,
                    query=query,
                )
                Clock.schedule_once(lambda *_: self._on_catalog_success(payload), 0)
            except requests.HTTPError as e:
                statusCode = e.response.status_code if e.response is not None else None
                errorPayload: Any = None
                try:
                    errorPayload = e.response.json() if e.response is not None else None
                except Exception:
                    errorPayload = {"detail": str(e)}
                Clock.schedule_once(lambda *_: self._on_catalog_error(statusCode, errorPayload), 0)
            except Exception as e:
                Clock.schedule_once(lambda *_: self._on_catalog_error(None, {"detail": str(e)}), 0)

        threading.Thread(target=worker, daemon=True).start()


    def _on_catalog_success(self, payload: Any) -> None:
        self.isLoading = False

        if not isinstance(payload, dict) or payload.get("status") is not True:
            self.statusText = f"Неожиданный ответ каталога: {payload}"
            self.recentFilesRvData = []
            return

        items = payload.get("data") or []
        if not isinstance(items, list):
            self.statusText = f"Неожиданный формат data: {payload}"
            self.recentFilesRvData = []
            return

        mapped = []
        for item in items:
            if not isinstance(item, dict):
                continue
            fileName = str(item.get("fileName") or "")
            rows = int(item.get("rows") or 0)

            mapped.append({
                "fileName": fileName,
                "dateText": "",
                "statusText": "Успешно",
                "countText": f"+{rows} транзакций",
            })

        self.recentFilesRvData = mapped
        self.statusText = "" if mapped else "Каталог пуст."


    def _on_catalog_error(self, statusCode: Any, errorPayload: Any) -> None:
        self.isLoading = False
        if statusCode is not None:
            self.statusText = f"Ошибка каталога ({statusCode}): {errorPayload}"
        else:
            self.statusText = f"Ошибка каталога: {errorPayload}"
        self.recentFilesRvData = []

    def on_back_click(self) -> None:
        if self.manager:
            self.manager.current = "transactions"

    def on_manual_upload_click(self) -> None:
        if self.manager:
            self.manager.current = "manual_transaction"

    def on_bank_click(self, bank_slug: str) -> None:
        """bank_slug:alfa / tinkoff / sber"""
        if self.isLoading:
            return

        if not self._sessionService.is_authorized():
            self.statusText = "Сессия не найдена. Авторизуйтесь."
            return

        self._activeBankSlug = bank_slug
        self.statusText = f"Выберите файл выписки для банка: {bank_slug}"
        self._open_file_picker()

    # ---------------- File picker (ПК + Android) ----------------
    def _open_file_picker(self) -> None:
        try:
            from plyer import filechooser
        except Exception:
            filechooser = None

        if filechooser is not None:
            try:
                filechooser.open_file(
                    on_selection=self._on_file_selected,
                    multiple=False,
                )
                return
            except Exception:
                pass

        self._open_kivy_filechooser_popup()

    def _open_kivy_filechooser_popup(self) -> None:
        chooser = FileChooserListView(path=".", filters=["*.pdf", "*.csv", "*.ofx", "*.xlsx", "*.xls", "*.*"])

        rootBox = BoxLayout(orientation="vertical", spacing=8, padding=8)
        rootBox.add_widget(chooser)

        buttonsRow = BoxLayout(size_hint_y=None, height=44, spacing=8)

        cancelBtn = Button(text="Отмена")
        okBtn = Button(text="Выбрать")

        buttonsRow.add_widget(cancelBtn)
        buttonsRow.add_widget(okBtn)

        rootBox.add_widget(buttonsRow)

        popup = Popup(title="Выбор файла выписки", content=rootBox, size_hint=(0.92, 0.92))
        self._filePickerPopup = popup

        def on_cancel(*_args) -> None:
            popup.dismiss()
            self.statusText = "Выбор файла отменён."

        def on_ok(*_args) -> None:
            selection = chooser.selection or []
            popup.dismiss()
            self._on_file_selected(selection)

        cancelBtn.bind(on_release=on_cancel)
        okBtn.bind(on_release=on_ok)

        popup.open()

    def _on_file_selected(self, selection: list[str]) -> None:
        if not selection:
            self.statusText = "Файл не выбран."
            return

        if self._activeBankSlug is None:
            self.statusText = "Не выбран банк для загрузки."
            return

        filePath = selection[0]
        bankSlug = self._activeBankSlug

        self.statusText = f"Загрузка файла в API: {filePath}"
        print(f"[TransactionsUploadScreen] selected file => {filePath} for slug={bankSlug}")

        self._upload_file_to_api(bankSlug=bankSlug, filePath=filePath)

    # ---------------- API upload ----------------
    def _upload_file_to_api(self, bankSlug: str, filePath: str) -> None:
        if self.isLoading:
            return

        self.isLoading = True

        userName = self._sessionService._sessionData.userName
        password = self._sessionService._sessionData.password

        query = PostBankTransactionsQuery(slug=bankSlug)

        self._run_request_in_thread(
            request_func=lambda: self._apiClient.post_bank_transactions_by_file(
                userName=userName,
                password=password,
                filePath=filePath,
                query=query,
            ),
            on_success=self._on_upload_success,
            on_error=self._on_upload_error,
        )

    def _on_upload_success(self, payload: Any) -> None:
        self.isLoading = False

        if isinstance(payload, dict):
            fileName = payload.get("file")
            loadedRows = payload.get("loaded rows")

            if fileName is not None and loadedRows is not None:
                self.statusText = f"Успешно: {fileName}, загружено строк: {loadedRows}"
            else:
                self.statusText = f"Успешно: {payload}"
        else:
            self.statusText = "Успешно, но ответ API не JSON"

        print(f"[TransactionsUploadScreen] upload success => {payload}")

    def _on_upload_error(self, statusCode: Optional[int], errorPayload: Any) -> None:
        self.isLoading = False

        detail = ""
        if isinstance(errorPayload, dict) and isinstance(errorPayload.get("detail"), str):
            detail = errorPayload["detail"].strip()

        if statusCode is not None:
            self.statusText = f"Ошибка загрузки ({statusCode}): {detail or errorPayload}"
        else:
            self.statusText = f"Ошибка загрузки: {detail or errorPayload}"

        print(f"[TransactionsUploadScreen] upload error => {statusCode}, {errorPayload}")

    # ---------------- threading helper ----------------
    def _run_request_in_thread(
        self,
        request_func,
        on_success,
        on_error,
    ) -> None:
        def worker() -> None:
            try:
                result = request_func()
                Clock.schedule_once(lambda *_: on_success(result), 0)
            except requests.HTTPError as e:
                status_code = None
                payload = None
                try:
                    status_code = e.response.status_code if e.response is not None else None
                    payload = e.response.json() if e.response is not None else None
                except Exception:
                    payload = None
                Clock.schedule_once(lambda *_: on_error(status_code, payload), 0)
            except Exception as e:
                Clock.schedule_once(lambda *_: on_error(None, {"detail": str(e)}), 0)

        threading.Thread(target=worker, daemon=True).start()
