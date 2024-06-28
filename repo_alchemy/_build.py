import abc
from typing import final

from sqlalchemy import ColumnElement, Select, select

from ._base import ModelProtocol
from ._filters import StatementFilter


class DefaultBuildSql[T: "ModelProtocol"]:
    """Тип билдера запроса  по умолчанию."""

    _model: type[T]

    @final
    def __init__(self, model: type[T]):
        self._model = model

    @final
    def build(
        self,
        *filters: StatementFilter | ColumnElement[bool],
    ):

        statement, models_by_filter = self._stmt()

        # Для формирования statement
        return self._apply_filters(
            statement,
            models_by_filter,
            *filters,
        )

    def _stmt(self) -> tuple[Select[tuple[T]], list[type[T]]]:
        """Метод для генерации составления запроса.
        example:
            select(self._model), [self._model]
        """

        return select(self._model), [self._model]

    @final
    def _filter_by_expression(
        self,
        statement: Select[tuple[T]],
        expression: ColumnElement[bool],
    ) -> Select[tuple[T]]:
        """Обработка фильтров типа expression"""

        return statement.where(
            expression,
        )

    @final
    def _apply_filters(
        self,
        statement: Select[tuple[T]],
        models_by_filters: list[type[T]],
        *filters: StatementFilter | ColumnElement[bool],
    ) -> Select[tuple[T]]:
        """Метод для выполнения фильтрации"""

        for flt in filters:
            if isinstance(flt, StatementFilter):
                statement = flt.append_to_statement(
                    statement,
                    models_by_filters,
                )
            else:
                statement = self._filter_by_expression(statement, flt)

        return statement


class BaseBuildSql[T: "ModelProtocol"](DefaultBuildSql, abc.ABC):
    """Базовый класс для сборки запросов"""

    @abc.abstractmethod
    def _stmt(self) -> tuple[Select[tuple[T]], list[type[T]]]:
        """
        example:
            select(self._model), [self._model]
        """

        raise NotImplementedError
