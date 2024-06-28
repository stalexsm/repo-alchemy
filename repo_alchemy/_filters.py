import abc
import datetime
from dataclasses import dataclass
from operator import attrgetter
from typing import Any, Callable, Collection, Literal, cast, final

from sqlalchemy import ColumnElement, Select, and_, between, or_, text
from sqlalchemy.orm import InstrumentedAttribute

from ._base import ModelProtocol
from ._types import DatesType

__all__ = (
    "AfterFilter",
    "BeforeFilter",
    "DatesTypeFilter",
    "EqFilter",
    "InFilter",
    "LimitOffset",
    "NotInFilter",
    "OnAfterFilter",
    "OnBeforeFilter",
    "OrderBy",
    "SearchFilter",
    "StatementFilter",
)

MappingToAttr = dict[str, InstrumentedAttribute[Any]]


class StatementFilter[T: "ModelProtocol"](abc.ABC):
    """Base Filter"""

    @abc.abstractmethod
    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        *args: Any,
        **kwargs: Any,
    ) -> Select[tuple[T]]:

        raise NotImplementedError

    @final
    def _get_instrumented_attr(
        self,
        models: list[type[T]],
        key: str | InstrumentedAttribute[Any],
    ) -> InstrumentedAttribute[Any]:
        """Getting an attribute from models"""

        if isinstance(key, InstrumentedAttribute):
            key = key.key

        for model in models:
            if hasattr(model, key):
                return cast("InstrumentedAttribute[Any]", getattr(model, key))

        raise AttributeError(
            f"The `{key}` is not in these models: [{", ".join(str(m.__table__.name) for m in models)}]."  # type: ignore
            "Check the correctness of the SQL request."
        )


@dataclass
class LimitOffset[T: "ModelProtocol"](StatementFilter):
    """Data required to add limit/offset filtering to a query."""

    limit: int
    offset: int

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:

        return statement.limit(self.limit).offset(self.offset)


@dataclass
class OrderBy[T: "ModelProtocol"](StatementFilter):
    """Data required to construct a ``ORDER BY ...`` clause."""

    field_name: str | None
    sort_order: Literal["asc", "desc"] = "asc"
    mapping_to_attr: MappingToAttr | None = None

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:

        if not self.field_name:
            return statement

        if self.mapping_to_attr and self.field_name in self.mapping_to_attr:
            field = self.mapping_to_attr[self.field_name]
        else:
            field = self._get_instrumented_attr(models, self.field_name)

        if self.sort_order == "desc":
            return statement.order_by(
                field.desc(),
            )

        return statement.order_by(
            field.asc(),
        )


@dataclass
class EqFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to construct a ``WHERE field_name == :value`` clause."""

    """Name of the model attribute to search on."""
    field_name: str

    """Values."""
    value: Any

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:

        if not self.value:
            return statement

        field = self._get_instrumented_attr(models, self.field_name)

        return statement.where(field == self.value)


@dataclass
class DatesTypeFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to construct a ``WHERE field_name >= <= BETWEEN :value`` clause."""

    """Name of the model attribute to search on."""
    field_name: str

    """Values."""
    value: DatesType | None

    def _get_min_max(self) -> tuple[Any, Any]:
        """Обработка min max"""

        min = self.value.min  # type: ignore
        max = self.value.max  # type: ignore

        if min == "none":
            min = None

        if max == "none":
            max = None

        if isinstance(min, datetime.datetime):
            min = min.replace(hour=0, minute=0, second=0)

        # Обработка DateTime
        if isinstance(max, datetime.datetime):
            max = max.replace(hour=23, minute=59, second=59)

        return min, max

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:

        if not self.value:
            return statement

        field = self._get_instrumented_attr(models, self.field_name)

        min, max = self._get_min_max()

        if all([min, max]):  # Обработка DateTime
            statement = statement.where(between(field, min, max))
        else:
            if min or max:
                if min:
                    statement = statement.where(field >= min)

                if max:
                    statement = statement.where(field <= max)

        return statement


@dataclass
class SearchFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to construct a ``WHERE field_name LIKE '%' || :value || '%'`` clause."""

    """Name of the model attribute to search on."""
    field_name: str

    """Values for ``NOT LIKE`` clause."""
    value: str | None

    """Should the search be case insensitive."""
    ignore_case: bool | None = True

    """Mapping To InstrumentedAttribute."""
    mapping_to_attr: InstrumentedAttribute[Any] | None = None

    @property
    def _operator(self) -> Callable[..., ColumnElement[bool]]:
        return or_

    @property
    def _func(self) -> attrgetter:
        return attrgetter("ilike" if self.ignore_case else "like")

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:

        if not self.value:
            return statement

        if self.mapping_to_attr:
            field = self.mapping_to_attr
        else:
            field = self._get_instrumented_attr(models, self.field_name)

        return statement.where(
            self._func(field)(f"%{self.value}%"),
        )


@dataclass
class NotInSearchFilter(SearchFilter):
    """Data required to construct a ``WHERE field_name NOT LIKE '%' || :value || '%'`` clause."""

    @property
    def _operator(self) -> Callable[..., ColumnElement[bool]]:
        return and_

    @property
    def _func(self) -> attrgetter:
        return attrgetter("not_ilike" if self.ignore_case else "not_like")


@dataclass
class InFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to construct a ``WHERE ... IN (...)`` clause."""

    """Name of the model attribute to filter on."""
    field_name: str

    """Values for ``IN`` clause."""
    values: Collection[T] | None

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:
        field = self._get_instrumented_attr(models, self.field_name)
        if self.values is None:
            return statement
        if not self.values:
            return statement.where(text("1=-1"))

        return statement.where(field.in_(self.values))


@dataclass
class NotInFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to construct a ``WHERE ... NOT IN (...)`` clause."""

    """Name of the model attribute to filter on."""
    field_name: str

    """Values for ``NOT IN`` clause."""
    values: Collection[T] | None

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:
        field = self._get_instrumented_attr(models, self.field_name)
        if not self.values:
            return statement

        return statement.where(field.in_(self.values))


@dataclass
class BeforeFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to filter a query on a ``Any`` column."""

    """Name of the model attribute to filter on."""
    field_name: str

    """Filter results where field earlier than this."""
    value: Any

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:
        field = self._get_instrumented_attr(models, self.field_name)
        if self.value is not None:
            statement = statement.where(
                field < self.value,
            )

        return statement


@dataclass
class OnBeforeFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to filter a query on a ``Any`` column."""

    """Name of the model attribute to filter on."""
    field_name: str

    """Filter results where field earlier than this."""
    value: Any

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:
        field = self._get_instrumented_attr(models, self.field_name)
        if self.value is not None:
            statement = statement.where(
                field <= self.value,
            )

        return statement


@dataclass
class AfterFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to filter a query on a ``Any`` column."""

    """Name of the model attribute to filter on."""
    field_name: str

    """Filter results where field earlier than this."""
    value: Any

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:
        field = self._get_instrumented_attr(models, self.field_name)
        if self.value is not None:
            statement = statement.where(
                field > self.value,
            )

        return statement


@dataclass
class OnAfterFilter[T: "ModelProtocol"](StatementFilter):
    """Data required to filter a query on a ``Any`` column."""

    """Name of the model attribute to filter on."""
    field_name: str

    """Filter results where field earlier than this."""
    value: Any

    def append_to_statement(
        self,
        statement: Select[tuple[T]],
        models: list[type[T]],
    ) -> Select[tuple[T]]:
        field = self._get_instrumented_attr(models, self.field_name)
        if self.value is not None:
            statement = statement.where(
                field >= self.value,
            )

        return statement
