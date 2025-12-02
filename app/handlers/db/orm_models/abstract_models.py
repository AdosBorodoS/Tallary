from datetime import date, datetime
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy import ForeignKey, PrimaryKeyConstraint, Index
from sqlalchemy import (Integer, Date, DateTime, String, BigInteger, Float, Text, Boolean, Enum)
from sqlalchemy.orm import Mapped, mapped_column, relationship,DeclarativeBase

class ConvToDict:
    def to_dict(self):
        return {row.name: getattr(self, row.name) if not isinstance(getattr(self, row.name), datetime) else str(getattr(self, row.name)) for row in self.__table__.columns}

class AbstractBaseModel(DeclarativeBase, ConvToDict):
    pass

class AbstractAlfaFinancialTransactions(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "abstract_alfa_financial_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    postingDate: Mapped[date] = mapped_column(Date, nullable=True)
    code: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    currencyAmount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=True)

class AbstractTinkoffFinancialTransactions(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "abstract_tinkoff_financial_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    postingDate: Mapped[date] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    description2: Mapped[str] = mapped_column(String, nullable=True)
    currencyAmount: Mapped[float] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)