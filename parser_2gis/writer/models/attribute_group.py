from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel


class AttributeGroup(BaseModel):
    # Название группы атрибутов (например "Кухня", "Услуги")
    name: str | None = None

    # Список атрибутов группы. Хранится как есть — нам нужно лишь их количество
    # как мера функциональной насыщенности объекта.
    attributes: List[Any] = []
