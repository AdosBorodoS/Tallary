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


class AbstractUsers(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "user.abstract_users_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userName: Mapped[int] = mapped_column(String, nullable=False)
    password: Mapped[int] = mapped_column(String, nullable=False)

class AbstractBankTransactions(AbstractBaseModel):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False) 
    fileName: Mapped[str] = mapped_column(String, nullable=False)
    operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    currencyAmount: Mapped[float] = mapped_column(Float, nullable=True)


class AbstractAlfaFinancialTransactions(AbstractBankTransactions):
    __abstract__ = True
    __tablename__ = "bank.abstract_alfa_financial_transactions"

    # id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    # userID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False) 
    # fileName: Mapped[str] = mapped_column(String, nullable=False)
    # operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    postingDate: Mapped[date] = mapped_column(Date, nullable=True)
    code: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    # description: Mapped[str] = mapped_column(String, nullable=True)
    # currencyAmount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=True)
    
class AbstractTinkoffFinancialTransactions(AbstractBankTransactions):
    __abstract__ = True
    __tablename__ = "bank.abstract_tinkoff_financial_transactions"
    
    # id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    # userID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False) 
    # fileName: Mapped[str] = mapped_column(String, nullable=False)
    # operationDate: Mapped[date] = mapped_column(Date, nullable=False)
    postingDate: Mapped[date] = mapped_column(Date, nullable=True)
    # description: Mapped[str] = mapped_column(String, nullable=True)
    description2: Mapped[str] = mapped_column(String, nullable=True)
    # currencyAmount: Mapped[float] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)

class AbstractGoalsCatalog(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "goal.abstract_goals_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    # userID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False) 
    goalName: Mapped[str] = mapped_column(String, nullable=False)


class AbstractGoalsOwnersCatalog(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "goal.abstract_goals_owners_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False) 
    goalID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractGoalsCatalog.__tablename__}.id"), nullable=False)

class Operations(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    EQ = "=="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="

class AbstractGoalsRule(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "goal.abstract_goals_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    goalID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractGoalsCatalog.__tablename__}.id"), nullable=False)
    goalOperation: Mapped[str] = mapped_column(String, nullable=False)
    goalRule: Mapped[int] = mapped_column(Integer, nullable=False)


class AbstractFriendsCatalog(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "user.abstract_friends_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False)
    friendID : Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False) 

class AbstractCastomCategorysCatalog(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "category.abstract_user_category_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    userID: Mapped[int] = mapped_column(Integer,ForeignKey(f"{AbstractUsers.__tablename__}.id"), nullable=False)
    categoryName: Mapped[str] = mapped_column(String, nullable=False)

class AbstractCastomCategorysConditions(AbstractBaseModel):
    __abstract__ = True
    __tablename__ = "category.abstract_user_category_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    categoryID: Mapped[int] = mapped_column(Integer, ForeignKey(f"{AbstractCastomCategorysCatalog.__tablename__}.id"), nullable=False)
    conditionValue: Mapped[str] = mapped_column(String, nullable=False)
    isExact: Mapped[str] = mapped_column(Boolean, nullable=False)
