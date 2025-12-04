import re
import os
import fitz
import pdfplumber
import pandas as pd
from datetime import datetime
from abc import ABC, abstractmethod


class AbstractSyupplyer(ABC):
    @abstractmethod
    def __init__(self, logerHandler):
        super().__init__()
        self.logerHandler = logerHandler

    @abstractmethod
    def preprocessing_data(self, dataPath:str)-> pd.DataFrame:
        pass

class AlfaPreprocessingDataFileHandler(AbstractSyupplyer):
    def __init__(self, logerHandler):
        super().__init__(logerHandler)
    
    def preprocessing_data(self, dataPath:str)-> pd.DataFrame:

        df = pd.read_excel(dataPath)

        columnsNameIndex = df[df['Unnamed: 0'] == 'Дата операции'].index.to_list()[0]
        df.columns = [x.replace('\xa0',' ') if isinstance(x,str) else f"Unnamed {ind}"  for ind,x in enumerate(df.iloc[columnsNameIndex].values)]
        df = df.iloc[columnsNameIndex+1:].reset_index(drop=True)
        df = df.iloc[:df[df['Дата операции'].isna()].index.min()]

        df = df[[x for x in df.columns if 'Unnamed' not in x]]

        df = df.rename(columns={
            "Дата операции": "operationDate",
            "Дата проводки": "postingDate",
            "Код":"code",
            "Категория": "category",
            "Описание": "description",
            "Сумма в валюте счета": "currencyAmount",
            "Статус ": "status",
        })

        df["currencyAmount"] = [float(x.replace("\xa0",'').replace(",",'.')) for x in df["currencyAmount"]]
        df["operationDate"] = [datetime.strptime(x,"%d.%m.%Y").date() if x != "HOLD" else datetime(1970,1,1).date() for x in df["operationDate"]]
        df["postingDate"] = [datetime.strptime(x,"%d.%m.%Y").date() if x != "HOLD" else datetime(1970,1,1).date() for x in df["postingDate"]]

        return df

class TinkoffPreprocessingDataFileHandler(AbstractSyupplyer):
    def __init__(self, logerHandler):
        super().__init__(logerHandler)

    @staticmethod
    def extract_tinkoff_pymupdf(pdfPath, excelPath, writeExcel=False) -> pd.DataFrame:
        doc = fitz.open(pdfPath)
        rows = []

        for page in doc:
            blocks = page.get_text("blocks")
            for b in blocks:
                text = b[4]
                if "описание" in text.lower() and "дата" in text.lower():
                    # нашли начало таблицы
                    continue

                if "₽" in text:  # heuristic: строки таблицы содержат ₽
                    parts = [x.strip() for x in text.split("  ") if x.strip()]
                    rows.append(parts)

        df = pd.DataFrame(rows)
        if writeExcel:
            df.to_excel(excelPath, index=False)

        return df

    @staticmethod
    def filter_rows_by_date(df: pd.DataFrame) -> pd.DataFrame:
        datePattern = re.compile(r"^\s*\d{2}\.\d{2}\.\d{2,4}")
        filteredRows = []
        for _, row in df.iterrows():
            cell = row.iloc[0]
            if not isinstance(cell, str):
                continue
            # Проверяем каждую подстроку, но ВОЗВРАЩАЕМ всю строку
            lines = cell.split("\n")
            if any(datePattern.match(line.strip()) for line in lines):
                filteredRows.append(row)

        return pd.DataFrame(filteredRows)

    def preprocessing_data(self, dataPath: str, excelDataPath: str | None = None, writeExcel: bool = False) -> pd.DataFrame:
        df = self.extract_tinkoff_pymupdf(
            pdfPath=dataPath,
            excelPath=excelDataPath,
            writeExcel=writeExcel
        )

        df = pd.DataFrame([x.split('\n') for x in self.filter_rows_by_date(df)[0].to_list()],
                          columns=["operationDate", "postingDate", "amount", "currencyAmount", "description", 'description2'])

        df["currencyAmount"] = [float(x.replace("\xa0", '').replace(",", '.').replace("+", '').replace("₽", '').replace(" ", '')) for x in df["currencyAmount"]]
        df["amount"] = [float(x.replace("\xa0", '').replace(",", '.').replace("+", '').replace("₽", '').replace(" ", '')) for x in df["amount"]]
        df["operationDate"] = [datetime.strptime(x, "%d.%m.%y").date() if x != "HOLD" else datetime(1970, 1, 1).date() for x in df["operationDate"]]
        df["postingDate"] = [datetime.strptime(x, "%d.%m.%y").date() if x != "HOLD" else datetime(1970, 1, 1).date() for x in df["postingDate"]]

        return df