from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Dates(BaseModel):
    # Дата создания записи (например "2019-02-01T00:00:00Z")
    created_at: Optional[str] = None

    # Дата последнего обновления записи (например "2026-07-04T19:01:23Z")
    updated_at: Optional[str] = None
