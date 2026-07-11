from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Org(BaseModel):
    # Идентификатор сети
    id: str

    # Полное имя организации (например "Му-Му, кафе")
    name: str

    # Количество филиалов данной организации
    branch_count: int

    # Короткое собственное имя сети (например "Му-Му")
    primary: Optional[str] = None

    # Специализация / расширение имени сети (например "кафе")
    extension: Optional[str] = None
