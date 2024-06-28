import abc
from typing import Any, Sequence, overload

from sqlalchemy.engine.row import Row, RowMapping

from ._base import ModelProtocol


class Resolver[T: "ModelProtocol"](abc.ABC):
    """Класс отвечающий за преобразование ответа от SqlAlchemy."""

    @abc.abstractmethod
    def process_items(
        self,
        items: Sequence[T] | Sequence[Row[Any]] | Sequence[Any],
    ) -> Any:
        """Метод для преобразование ответа от SqlAlchemy."""
        ...

    @abc.abstractmethod
    def process_item(self, item: T | Row[Any] | Any) -> Any:
        """Метод для преобразование ответа от SqlAlchemy."""
        ...


class DefaultResolver[T: "ModelProtocol"](Resolver):
    """Базовый класс для преобразования возврата ответа от БД."""

    @overload
    def process_items(self, items: Sequence[T]) -> Sequence[T]: ...

    @overload
    def process_items(self, items: Sequence[Row[Any]]) -> Sequence[RowMapping]: ...

    def process_items(
        self, items: Sequence[T] | Sequence[Row[Any]]
    ) -> Sequence[T] | Sequence[RowMapping]:
        """Преобразование ответа от БД."""

        new_items = []
        for item in items:
            if isinstance(item, Row):
                new_items.append(item._mapping)
            else:
                new_items.append(item)

        return new_items

    @overload
    def process_item(self, item: T) -> T: ...

    @overload
    def process_item(self, item: None) -> None: ...

    @overload
    def process_item(self, item: Row[Any]) -> RowMapping: ...

    def process_item(
        self,
        item: T | Row[Any] | None,
    ) -> T | RowMapping | None:
        """Преобразование ответа от БД."""

        if isinstance(item, Row):
            return item._mapping

        return item


class BaseResolver[T: "ModelProtocol"](Resolver, abc.ABC):
    """Кастомный класс для преобразования возврата ответа от БД."""

    pass
