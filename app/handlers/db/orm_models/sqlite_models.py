# py -m app.handlers.db.orm_models.sqlite_models
import asyncio
import enum
from pathlib import Path
from datetime import datetime, timedelta, date

from sqlalchemy import (
    Date, Float, Column, Integer, Enum, 
    BigInteger, String, Boolean, DateTime, 
    Text, ForeignKey, UniqueConstraint, 
    PrimaryKeyConstraint, Index, UUID
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .abstract_models import (AbstractBaseModel,
                              AbstractAlfaFinancialTransactions,
                              AbstractTinkoffFinancialTransactions
                              )


class AlfaFinancialTransactions(AbstractAlfaFinancialTransactions):
    __abstract__ = False
    __tablename__ = "bank.alfa_financial_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    postingDate: Mapped[date] = mapped_column(Date, nullable=True)
    code: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    currencyAmount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=True)

class TinkoffFinancialTransactions(AbstractTinkoffFinancialTransactions):
    __abstract__ = False
    __tablename__ = "bank.tinkoff_financial_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    postingDate: Mapped[date] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    description2: Mapped[str] = mapped_column(String, nullable=True)
    currencyAmount: Mapped[float] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)



async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(AbstractBaseModel.metadata.create_all)

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parents[3]
    DB_PATH = BASE_DIR / "database" / "database_draft.db"
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    ASYNC_DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"
    engine = create_async_engine(ASYNC_DB_URL, echo=True, future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    asyncio.run(init_models())
