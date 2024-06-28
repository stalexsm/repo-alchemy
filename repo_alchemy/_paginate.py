import math


class DefaultPaginate:
    """Механизм отвечающий за пагиницию."""

    def paginate(self, cnt: int, limit: int = 30):
        """Получение кол-ва страниц"""

        if limit > 0:
            total = math.ceil(cnt / limit)
        else:
            total = cnt

        return total


class LoadPaginate:
    """Механизм отвечающий за пагиницию."""

    def paginate(self, cnt: int):
        """Получение кол-ва страниц"""

        return int(cnt)
