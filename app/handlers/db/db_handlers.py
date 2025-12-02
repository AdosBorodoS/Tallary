# sqlalchemy = "==2.0.42"
# aiosqlite = "==0.21.0"
from typing import List, Sequence, Tuple, Any
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from abc import ABC, abstractmethod

class BaseDataBaseHandler(ABC):

    @abstractmethod
    def create_session(self):
        pass

    @abstractmethod
    def get_table_data(self,columns, columnFilters):
        pass

    @abstractmethod
    def insert_data(self, data) -> None:
        pass

    @abstractmethod
    def delete_data(self, table, columnFilters) -> None:
        pass

class SqliteHandlerAsync(BaseDataBaseHandler):
    def __init__(self, url: str = "sqlite+aiosqlite:///database/database.db"):
        self.engine = create_async_engine(url, echo=False, future=True)
        self.Session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    def create_session(self) -> async_sessionmaker[AsyncSession]:
        return self.Session

    async def get_table_data(self, columns: List, columnFilters: Sequence, *args,**kwargs) -> List:
        async with self.Session() as sess:
            stmt = select(*columns)
            for f in columnFilters:
                stmt = stmt.where(f)
            if kwargs.get('limit'):
                stmt = stmt.limit(kwargs.get('limit'))
            result = await sess.execute(stmt)
            return result.scalars().all() if len(columns) == 1 else result.all()

    async def insert_data(self, data: List[Any]) -> None:
        async with self.Session() as sess:
            sess.add_all(data)
            await sess.commit()
        return [x.to_dict() for x in data]

    async def delete_data(self, table, columnFilters: Sequence = ()) -> int:
        async with self.Session() as sess:
            stmt = sa_delete(table)
            for f in columnFilters:
                stmt = stmt.where(f)
            result = await sess.execute(stmt)
            await sess.commit()
            return result.rowcount or 0