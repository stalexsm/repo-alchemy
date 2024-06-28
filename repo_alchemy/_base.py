from typing import Any, ClassVar, Protocol, runtime_checkable

from sqlalchemy import orm as so
from sqlalchemy.sql import FromClause


@runtime_checkable
class ModelProtocol(Protocol):
    """The base SQLAlchemy model protocol."""

    __table__: ClassVar[FromClause]
    __mapper__: ClassVar[so.Mapper[Any]]
    __name__: str
