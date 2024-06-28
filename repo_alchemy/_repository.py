from typing import Sequence, final

import sqlalchemy as sa
from sqlalchemy import ColumnElement
from sqlalchemy import orm as so

from ._base import ModelProtocol
from ._build import DefaultBuildSql
from ._filters import LimitOffset, StatementFilter
from ._paginate import DefaultPaginate
from ._resolver import DefaultResolver, Resolver


class Base[T: "ModelProtocol"]:
    """Базовый репозиторий"""

    _model: type[T]

    @final
    def __init__(self, session: so.Session):
        if not self._model:
            raise ValueError(
                f"No model is specified for this repository: {self.__class__.__name__}"
            )

        self.__session: so.Session = session  # Add Session
        self.__builder: DefaultBuildSql = DefaultBuildSql(self._model)  # Add Builder
        self.__resolver: Resolver = DefaultResolver()  # Add resolver
        self.__paginate: DefaultPaginate = DefaultPaginate()  # Add resolver

    @final
    def add(self, obj: T):
        """Add obj in session"""

        self.__session.add(obj)

    @final
    def add_all(self, objs: Sequence[T]):
        """Add all objs in session"""

        self.__session.add_all(objs)

    @final
    def delete(self, obj: T):
        """Delete obj in session"""

        self.__session.delete(obj)

    @final
    def get_list(
        self,
        *flt: StatementFilter | ColumnElement[bool],
        is_scalars: bool = True,
        builder: type[DefaultBuildSql] | None = None,
        resolver: type[Resolver] | None = None,
    ) -> Sequence[T]:
        """Получение списка сущностей без пагинации"""

        if builder:
            self.__builder = builder(self._model)

        statement = self.__builder.build(*flt)
        if is_scalars:
            rows = (
                self.__session.execute(
                    statement,
                )
                .scalars()
                .all()
            )
        else:
            rows = self.__session.execute(
                statement,
            ).all()

        if resolver:
            self.__resolver = resolver()

        rows = self.__resolver.process_items(rows)

        return rows

    @final
    def get_list_with_paginate(
        self,
        *flt: StatementFilter | ColumnElement[bool],
        is_scalars: bool = True,
        builder: type[DefaultBuildSql] | None = None,
        resolver: type[Resolver] | None = None,
        paginate: type[DefaultPaginate] | None = None,
    ) -> tuple[Sequence[T], int]:
        """Получение списка сущностей с пагинацией"""

        if builder:
            self.__builder = builder(self._model)

        statement = self.__builder.build(*flt)
        if is_scalars:
            rows = (
                self.__session.execute(
                    statement,
                )
                .scalars()
                .all()
            )
        else:
            rows = self.__session.execute(
                statement,
            ).all()

        # Пересобирем запрос для подсчета строк для пагинации
        statement = (
            statement.with_only_columns(
                sa.func.count(self._model.id), maintain_column_froms=True
            )
            .order_by(None)
            .limit(None)
            .offset(None)
        )

        cnt = (
            self.__session.execute(
                statement,
            ).scalar()
            or 0
        )

        if resolver:
            self.__resolver = resolver()

        rows = self.__resolver.process_items(rows)

        if paginate:
            self.__paginate = paginate()

        # Достаем кол-во на странице, чтобы обработать пагинацию.
        limit = 30
        for f in flt:
            if isinstance(f, LimitOffset):
                limit = f.limit

        return rows, self.__paginate.paginate(cnt, limit)

    @final
    def get_one(
        self,
        *flt: StatementFilter | ColumnElement[bool],
        is_scalars: bool = True,
        builder: type[DefaultBuildSql] | None = None,
        resolver: type[Resolver] | None = None,
    ) -> T | None:
        """Получение сущности"""

        if builder:
            self.__builder = builder(self._model)

        statement = self.__builder.build(*flt)
        if is_scalars:
            row = (
                self.__session.execute(
                    statement,
                )
                .scalars()
                .first()
            )
        else:
            row = self.__session.execute(
                statement,
            ).first()

        if resolver:
            self.__resolver = resolver()

        row = self.__resolver.process_item(row)

        return row
