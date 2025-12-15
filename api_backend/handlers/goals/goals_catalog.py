import json
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime, date
from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Tuple, List
from sqlalchemy import types as satypes
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .schema import UpdateGoalCatalog
from ..logers.loger_handlers import LogerHandler
from ..db.db_handlers import AbstractDataBaseHandler
from ..db.orm_models.abstract_models import AbstractGoalsCatalog

class AbstractGoalsCatalogHandler(ABC):
    @abstractmethod
    def __init__(self, logerHandler, dbHandler, dbt):
        super().__init__()
        self.logerHandler:LogerHandler = logerHandler
        self.dbHandler:AbstractDataBaseHandler = dbHandler
        self.dbt:AbstractGoalsCatalog = dbt 

    @abstractmethod
    def get_data(self):
        pass
    
    @abstractmethod
    def insert_data(self):
        pass
    
    @abstractmethod
    def delete_data(self):
        pass
    
    @abstractmethod
    def update_data(self):
        pass

class GoalsCatalogHandler(AbstractGoalsCatalogHandler):
    def __init__(self, logerHandler, dbHandler, dbt):
        super().__init__(logerHandler, dbHandler, dbt)

    async def get_data(self, columnFilters:List):
        return await self.dbHandler.get_table_data([self.dbt], columnFilters)

    async def insert_data(self, userID:int, goalName:str):
        createGoalResponse = await self.dbHandler.insert_data(
            data=(self.dbt(
                userID=userID,
                goalName=goalName
                ),
            )
        )
        return createGoalResponse
    
    async def delete_data(self, goalID:int):
        return await self.dbHandler.delete_data(self.dbt, (self.dbt.id == goalID,))

    @staticmethod
    def __coerce(val, col_type, nullable: bool):
        if val is None or (isinstance(val, str) and val.strip() == "" and nullable):
            return None

        t = col_type
        while hasattr(t, "impl"):
            t = t.impl

        if isinstance(t, (satypes.Integer, satypes.BigInteger, satypes.SmallInteger)):
            return int(val)

        if isinstance(t, (satypes.Float, satypes.Numeric)):
            return Decimal(str(val)) if isinstance(t, satypes.Numeric) else float(val)

        if isinstance(t, satypes.Boolean):
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                s = val.strip().lower()
                if s in {"1", "true", "t", "yes", "y", "on"}:
                    return True
                if s in {"0", "false", "f", "no", "n", "off"}:
                    return False
            raise ValueError(f"Cannot parse boolean from {val!r}")

        if isinstance(t, satypes.Date):
            if isinstance(val, date) and not isinstance(val, datetime):
                return val
            if isinstance(val, datetime):
                return val.date()
            if isinstance(val, str):
                return date.fromisoformat(val)
            raise ValueError(f"Cannot parse date from {val!r}")

        if isinstance(t, satypes.DateTime):
            if isinstance(val, datetime):
                return val
            if isinstance(val, date):
                return datetime.combine(val, datetime.min.time())
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val)
                except ValueError:
                    return datetime.fromisoformat(val.replace(" ", "T"))
            raise ValueError(f"Cannot parse datetime from {val!r}")

        if isinstance(t, satypes.Enum):
            allowed = set(t.enums or [])
            if isinstance(val, str):
                if not allowed or val in allowed:
                    return val
            raise ValueError(
                f"Invalid enum value {val!r}; allowed: {sorted(allowed)}")

        # JSON
        if isinstance(t, satypes.JSON):
            if isinstance(val, (dict, list, int, float, str, bool)) or val is None:
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        pass
                return val

        if isinstance(t, (satypes.String, satypes.Text, satypes.Unicode, satypes.UnicodeText, satypes.LargeBinary)):
            return val if isinstance(val, (bytes, bytearray)) and isinstance(t, satypes.LargeBinary) else str(val)

        return val

    @staticmethod
    def _to_updates_dict(upd: Any) -> Dict[str, Any]:
        if isinstance(upd, Mapping):
            return dict(upd)
        if isinstance(upd, BaseModel):
            return upd.model_dump(exclude_unset=True, exclude_none=True)
        return dict(upd)

    def __normalize_updates_for_model(self, updatesData: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        updatesData: Dict[str, Any] = self._to_updates_dict(updatesData)

        cols = {c.name: c for c in self.dbt.__table__.columns}
        valid: Dict[str, Any] = {}
        skipped: Dict[str, str] = {}

        for key, raw_val in updatesData.items():
            col = cols.get(key)
            if col is None:
                skipped[key] = "unknown column"
                continue
            if col.primary_key:
                skipped[key] = "primary key is not updatable"
                continue

            try:
                valid[key] = self.__coerce(
                    raw_val, col.type, nullable=col.nullable)
            except Exception as e:
                skipped[key] = f"conversion error: {e}"

        return valid, skipped

    async def update_data(self, goalID:int, updatesData: UpdateGoalCatalog):
        async with self.dbHandler.create_session()() as sess:
            try:
                obj = await sess.get(self.dbt, goalID)  # AsyncSession.get
                if obj is None:
                    return None
                valid, _ = self.__normalize_updates_for_model(updatesData.to_dict())
                for k, v in valid.items():
                    setattr(obj, k, v)
                await sess.commit()
                await sess.refresh(obj)
                return obj
            except (IntegrityError, SQLAlchemyError):
                await sess.rollback()
                raise
