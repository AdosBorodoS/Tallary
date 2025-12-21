# py -m api_backend.handlers.db.orm_models.sqlite_models
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

from .abstract_models import *


class Users(AbstractUsers):
    __abstract__ = False
    __tablename__ = "user.users_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userName: Mapped[int] = mapped_column(String, nullable=False)
    password: Mapped[int] = mapped_column(String, nullable=False)

class AlfaFinancialTransactions(AbstractAlfaFinancialTransactions):
    __abstract__ = False
    __tablename__ = "bank.alfa_financial_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{Users.__tablename__}.id"), nullable=False) 
    fileName: Mapped[str] = mapped_column(String, nullable=False)
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
    userID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{Users.__tablename__}.id"), nullable=False) 
    fileName: Mapped[str] = mapped_column(String, nullable=False)
    operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    postingDate: Mapped[date] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    description2: Mapped[str] = mapped_column(String, nullable=True)
    currencyAmount: Mapped[float] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)

class GoalsCatalog(AbstractGoalsCatalog):
    __abstract__ = False
    __tablename__ = "goal.goals_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    goalName: Mapped[str] = mapped_column(String, nullable=False)

class GoalsOwnersCatalog(AbstractGoalsOwnersCatalog):
    __abstract__ = False
    __tablename__ = "goal.goals_owners_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{Users.__tablename__}.id"), nullable=False) 
    goalID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{GoalsCatalog.__tablename__}.id"), nullable=False)

class GoalsRule(AbstractGoalsRule):
    __abstract__ = False
    __tablename__ = "goal.goals_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    goalID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{GoalsCatalog.__tablename__}.id"), nullable=False)
    goalOperation: Mapped[str] = mapped_column(String, nullable=False)
    goalRule: Mapped[int] = mapped_column(Integer, nullable=False)

class FriendsCatalog(AbstractFriendsCatalog):
    __abstract__ = False
    __tablename__ = "user.friends_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{Users.__tablename__}.id"), nullable=False)
    friendID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{Users.__tablename__}.id"), nullable=False) 

class CastomCategorysCatalog(AbstractCastomCategorysCatalog):
    __abstract__ = False
    __tablename__ = "category.user_category_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID: Mapped[int] = mapped_column(Integer, ForeignKey(f"{Users.__tablename__}.id"), nullable=False)
    categoryName: Mapped[str] = mapped_column(String, nullable=False)

class CastomCategorysConditions(AbstractCastomCategorysConditions):
    __abstract__ = False
    __tablename__ = "category.user_category_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    categoryID: Mapped[int] = mapped_column(Integer, ForeignKey(f"{CastomCategorysCatalog.__tablename__}.id"), nullable=False)
    conditionValue: Mapped[str] = mapped_column(String, nullable=False)
    isExact: Mapped[str] = mapped_column(Boolean, nullable=False)


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
