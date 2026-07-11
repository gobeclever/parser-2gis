from __future__ import annotations

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from ..chrome.options import default_memory_limit
from ..common import floor_to_hundreds


def default_max_records() -> int:
    """Try linear approximation for optimal max records."""
    max_records = floor_to_hundreds((550 * default_memory_limit() / 1024 - 400))
    return max_records if max_records > 0 else 1


class ParserOptions(BaseModel):
    """Represent all possible options for Parser.

    Attrubutes:
        skip_404_response: Whether to skip 404 document response or not.
        delay_between_clicks: Delay between each item's click in milliseconds.
        max_records: Max number of records to parse from one URL.
        use_gc: Use Garbage Collector.
        gc_pages_interval: Run Garbage Collector every N pages (if `use_gc` enabled).
    """
    skip_404_response: bool = True
    delay_between_clicks: NonNegativeInt = 0
    max_records: PositiveInt = default_max_records()
    use_gc: bool = False
    gc_pages_interval: PositiveInt = 10

    # Retry an unexpectedly empty results page (soft anti-bot) before giving up.
    empty_page_retries: NonNegativeInt = 3
    empty_page_retry_delay: NonNegativeInt = 4000  # ms

    # Restart the browser and resume from the current page if the tab crashes
    # (e.g. Out of Memory). 0 disables recovery.
    max_browser_restarts: NonNegativeInt = 5
