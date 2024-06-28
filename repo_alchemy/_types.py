import datetime
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class DatesType:
    """Специальный тип по обработки cdates | udates для операции"""

    min: datetime.datetime | datetime.date | Literal["none"] = "none"
    max: datetime.datetime | datetime.date | Literal["none"] = "none"
