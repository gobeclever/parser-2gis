from __future__ import annotations

import json
from typing import Any

from ...logger import logger
from .file_writer import FileWriter


class JSONLinesWriter(FileWriter):
    """Writer to a JSON Lines file (one JSON object per line).

    Unlike `JSONWriter`, there is no surrounding `[ ... ]` array, so the file
    stays valid even if the process is interrupted mid-run: every completed
    line is a self-contained record. Combined with a flush after each line,
    this makes the format robust for large, long-running jobs.
    """
    def __enter__(self) -> JSONLinesWriter:
        super().__enter__()
        self._wrote_count = 0
        return self

    def _writedoc(self, catalog_doc: Any) -> None:
        """Write a `catalog_doc` as a single JSON line."""
        item = catalog_doc['result']['items'][0]

        # Tag the item with the source query URL it came from
        if self._source_url is not None:
            item['source_url'] = self._source_url

        # Expected total count reported by 2GIS for the query
        if self._expected_count is not None:
            item['expected_count'] = self._expected_count

        if self._options.verbose:
            try:
                name = item['name_ex']['primary']
            except KeyError:
                name = '...'

            logger.info('Парсинг [%d] > %s', self._wrote_count + 1, name)

        self._file.write(json.dumps(item, ensure_ascii=False))
        self._file.write('\n')
        # Flush right away so an abrupt crash keeps all lines written so far.
        self._file.flush()
        self._wrote_count += 1

    def write(self, catalog_doc: Any) -> None:
        """Write Catalog Item API JSON document down to a JSON Lines file.

        Args:
            catalog_doc: Catalog Item API JSON document.
        """
        if not self._check_catalog_doc(catalog_doc):
            return

        self._writedoc(catalog_doc)
