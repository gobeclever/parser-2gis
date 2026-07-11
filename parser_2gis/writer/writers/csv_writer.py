from __future__ import annotations

import csv
import os
import re
import shutil
from typing import Any, Callable

from pydantic import ValidationError

from ...common import report_from_validation_error
from ...logger import logger
from ..models import CatalogItem
from .file_writer import FileWriter


class CSVWriter(FileWriter):
    """Writer to CSV table."""
    @property
    def _type_names(self) -> dict[str, str]:
        return {
            'parking': 'Парковка',
            'street': 'Улица',
            'road': 'Дорога',
            'crossroad': 'Перекрёсток',
            'station': 'Остановка',
        }

    @property
    def _complex_mapping(self) -> dict[str, Any]:
        # Complex mapping means its content could contain several entities bound by user settings.
        # For example: phone -> phone_1, phone_2, ..., phone_n
        return {
            'phone': 'Телефон', 'email': 'E-mail', 'website': 'Веб-сайт', 'instagram': 'Instagram',
            'twitter': 'Twitter', 'facebook': 'Facebook', 'vkontakte': 'ВКонтакте', 'whatsapp': 'WhatsApp',
            'viber': 'Viber', 'telegram': 'Telegram', 'youtube': 'YouTube', 'skype': 'Skype'
        }

    @property
    def _data_mapping(self) -> dict[str, Any]:
        data_mapping = {
            'name': 'Наименование', 'description': 'Описание', 'rubrics': 'Рубрики',
            'address': 'Адрес', 'address_comment': 'Комментарий к адресу',
            'postcode': 'Почтовый индекс', 'living_area': 'Микрорайон', 'district': 'Район', 'city': 'Город',
            'district_area': 'Округ', 'region': 'Регион', 'country': 'Страна', 'schedule': 'Часы работы',
            'timezone': 'Часовой пояс', 'general_rating': 'Рейтинг', 'general_review_count': 'Количество отзывов'
        }

        # Expand complex mapping
        for k, v in self._complex_mapping.items():
            for n in range(1, self._options.csv.columns_per_entity + 1):
                data_mapping[f'{k}_{n}'] = f'{v} {n}'

        if not self._options.csv.add_rubrics:
            data_mapping.pop('rubrics', None)

        return {
            **data_mapping,
            **{
                'id': 'ID объекта',
                'point_lat': 'Широта',
                'point_lon': 'Долгота',
                'building_id': 'ID здания',
                'building_name': 'Название здания',
                'floor_id': 'ID этажа',
                'branch_count': 'Количество филиалов',
                'org_id': 'ID сети',
                'org_name': 'Название сети',
                'org_specialization': 'Специализация сети',
                'primary_rubric': 'Главная рубрика',
                'poi_category': 'POI-категория',
                'rubric_count': 'Кол-во рубрик',
                'attributes_count': 'Кол-во атрибутов',
                'updated_at': 'Дата обновления',
                'is_deleted': 'Удалён',
                'segment_id': 'ID сегмента',
                'region_id': 'ID региона',
                'url': '2GIS URL',
                'type': 'Тип',
                'expected_count': 'Ожидаемое кол-во (2GIS)',
                'source_url': 'Ссылка запроса',
            }
        }

    def _writerow(self, row: dict[str, Any]) -> None:
        """Write a `row` into CSV."""
        if self._options.verbose:
            logger.info('Парсинг [%d] > %s', self._wrote_count + 1, row['name'])

        try:
            self._writer.writerow(row)
            # Flush to the OS right away so an abrupt crash keeps all
            # records written so far (cheap: no forced disk sync).
            self._file.flush()
        except Exception as e:
            logger.error('Ошибка во время записи: %s', e)

    def __enter__(self) -> CSVWriter:
        super().__enter__()
        self._writer = csv.DictWriter(self._file, self._data_mapping.keys())
        self._writer.writerow(self._data_mapping)  # Write header
        self._wrote_count = 0
        return self

    def __exit__(self, *exc_info) -> None:
        super().__exit__(*exc_info)
        if self._options.csv.remove_empty_columns:
            logger.info('Удаление пустых колонок CSV.')
            self._remove_empty_columns()
        if self._options.csv.remove_duplicates:
            logger.info('Удаление повторяющихся записей CSV.')
            self._remove_duplicates()

    def _remove_empty_columns(self) -> None:
        """Post-process: Remove empty columns."""
        complex_columns = self._complex_mapping.keys()
        complex_columns_count = {c: 0 for c in self._data_mapping.keys() if
                                 re.match('|'.join(fr'^{x}_\d+$' for x in complex_columns), c)}

        # Looking for empty columns
        with self._open_file(self._file_path, 'r') as f_csv:
            csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore
            next(csv_reader, None)  # Skip header
            for row in csv.DictReader(f_csv, self._data_mapping.keys()):  # type: ignore
                for column_name in complex_columns_count.keys():
                    if row[column_name] != '':
                        complex_columns_count[column_name] += 1

        # Generate new data mapping
        new_data_mapping: dict[str, Any] = {}
        for k, v in self._data_mapping.items():
            if k in complex_columns_count:
                if complex_columns_count[k] > 0:
                    new_data_mapping[k] = v
            else:
                new_data_mapping[k] = v

        # Rename single complex column - remove postfix numbers
        for column in complex_columns:
            if f'{column}_1' in new_data_mapping and f'{column}_2' not in new_data_mapping:
                new_data_mapping[f'{column}_1'] = re.sub(r'\s+\d+$', '', new_data_mapping[f'{column}_1'])

        # Populate new csv
        tmp_csv_name = os.path.splitext(self._file_path)[0] + '.removed-columns.csv'

        with self._open_file(tmp_csv_name, 'w') as f_tmp_csv, \
                self._open_file(self._file_path, 'r') as f_csv:
            csv_writer = csv.DictWriter(f_tmp_csv, new_data_mapping.keys())  # type: ignore
            csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore
            csv_writer.writerow(new_data_mapping)  # Write new header
            next(csv_reader, None)  # Skip header

            for row in csv_reader:
                new_row = {k: v for k, v in row.items() if k in new_data_mapping}
                csv_writer.writerow(new_row)

        # Replace original table with new one
        shutil.move(tmp_csv_name, self._file_path)

    def _remove_duplicates(self) -> None:
        """Post-process: Remove duplicates."""
        tmp_csv_name = os.path.splitext(self._file_path)[0] + '.deduplicated.csv'
        with self._open_file(tmp_csv_name, 'w') as f_tmp_csv, \
                self._open_file(self._file_path, 'r') as f_csv:
            seen_records = set()
            for line in f_csv:
                if line in seen_records:
                    continue

                seen_records.add(line)
                f_tmp_csv.write(line)

        # Replace original table with new one
        shutil.move(tmp_csv_name, self._file_path)

    def write(self, catalog_doc: Any) -> None:
        """Write Catalog Item API JSON document down to CSV table.

        Args:
            catalog_doc: Catalog Item API JSON document.
        """
        if not self._check_catalog_doc(catalog_doc):
            return

        row = self._extract_raw(catalog_doc)
        if row:
            self._writerow(row)
            self._wrote_count += 1

    def _extract_fallback(self, item: dict[str, Any]) -> dict[str, Any]:
        """Defensive extraction straight from the raw item dict.

        Used when strict model validation fails: instead of losing the whole
        record, we salvage as many fields as possible (each read is guarded,
        so nothing here can raise). Priority fields — name, address, coords,
        rubrics, category — are almost always present and get filled.
        """
        data: dict[str, Any] = {k: None for k in self._data_mapping.keys()}

        def g(d: Any, *keys: str) -> Any:
            """Safe nested get."""
            for k in keys:
                if not isinstance(d, dict):
                    return None
                d = d.get(k)
            return d

        try:
            # Name / description
            name_ex = item.get('name_ex') or {}
            if name_ex.get('primary'):
                data['name'] = name_ex.get('primary')
                data['description'] = name_ex.get('extension')
            elif item.get('name'):
                data['name'] = item.get('name')
            elif item.get('type') in self._type_names:
                data['name'] = self._type_names[item['type']]

            data['type'] = item.get('type')
            data['address'] = item.get('address_name')
            data['address_comment'] = item.get('address_comment')

            # Reviews
            data['general_rating'] = g(item, 'reviews', 'general_rating')
            data['general_review_count'] = g(item, 'reviews', 'general_review_count')

            # Point
            data['point_lat'] = g(item, 'point', 'lat')
            data['point_lon'] = g(item, 'point', 'lon')

            # Address details
            data['postcode'] = g(item, 'address', 'postcode')
            data['building_id'] = g(item, 'address', 'building_id')
            data['building_name'] = g(item, 'address', 'building_name')

            # Timezone
            offset = item.get('timezone_offset')
            if isinstance(offset, int):
                sign = '-' if offset < 0 else '+'
                m = abs(offset)
                data['timezone'] = '{}{:02d}:{:02d}'.format(sign, m // 60, m % 60)

            # Administrative division
            for div in item.get('adm_div') or []:
                t = div.get('type')
                if t in ('country', 'region', 'district_area', 'city', 'district', 'living_area') and div.get('name'):
                    data[t] = div.get('name')

            # Identity / URL
            iid = item.get('id')
            if isinstance(iid, str):
                data['id'] = iid.split('_')[0]
                data['url'] = 'https://2gis.com/firm/%s' % iid.split('_')[0]
            data['floor_id'] = item.get('floor_id')
            data['segment_id'] = item.get('segment_id')
            data['region_id'] = item.get('region_id')
            data['is_deleted'] = item.get('is_deleted')

            # Organization / chain
            org = item.get('org') or {}
            if org:
                data['branch_count'] = org.get('branch_count')
                data['org_id'] = org.get('id')
                data['org_name'] = org.get('primary') or org.get('name')
                data['org_specialization'] = org.get('extension')

            # Rubrics
            rubrics = item.get('rubrics') or []
            if self._options.csv.add_rubrics:
                data['rubrics'] = self._options.csv.join_char.join(
                    r.get('name') for r in rubrics if r.get('name'))
            data['primary_rubric'] = next(
                (r.get('name') for r in rubrics if r.get('kind') == 'primary'), None)
            data['rubric_count'] = len(rubrics)

            # POI category
            data['poi_category'] = item.get('poi_category')

            # Attributes count
            data['attributes_count'] = sum(
                len(grp.get('attributes') or []) for grp in item.get('attribute_groups') or [])

            # Update date
            data['updated_at'] = g(item, 'dates', 'updated_at')

            # Contacts (best-effort, simplified)
            counters: dict[str, int] = {}
            url_types = ('website', 'vkontakte', 'whatsapp', 'viber', 'telegram',
                         'instagram', 'facebook', 'twitter', 'youtube', 'skype')
            for grp in item.get('contact_groups') or []:
                for c in grp.get('contacts') or []:
                    ctype = c.get('type')
                    if ctype not in self._complex_mapping:
                        continue
                    if ctype == 'phone':
                        raw = c.get('text') or c.get('value')
                        val = re.sub(r'^\+7', '8', re.sub(r'[^0-9+]', '', raw)) if raw else None
                    elif ctype in url_types:
                        val = c.get('url') or c.get('value')
                    else:
                        val = c.get('value') or c.get('url')
                    if not val:
                        continue
                    if ctype == 'whatsapp':
                        val = val.split('?')[0]
                    counters[ctype] = counters.get(ctype, 0) + 1
                    col = f'{ctype}_{counters[ctype]}'
                    if col in data:
                        data[col] = val
        except Exception as e:
            # Should never happen (all reads are guarded), but never let the
            # salvage path itself break the run.
            logger.error('Ошибка резервного извлечения: %s', e)

        # Meta columns
        data['expected_count'] = self._expected_count
        data['source_url'] = self._source_url
        return data

    def _extract_raw(self, catalog_doc: Any) -> dict[str, Any]:
        """Extract data from Catalog Item API JSON document.

        Args:
            catalog_doc: Catalog Item API JSON document.

        Returns:
            Dictionary for CSV row.
        """
        data: dict[str, Any] = {k: None for k in self._data_mapping.keys()}

        item = catalog_doc['result']['items'][0]

        try:
            catalog_item = CatalogItem(**item)
        except ValidationError as e:
            errors = []
            errors_report = report_from_validation_error(e, item)
            for path, description in errors_report.items():
                arg = description['invalid_value']
                error_msg = description['error_message']
                errors.append(f'[*] Поле: {path}, значение: {arg}, ошибка: {error_msg}')

            # Don't drop the whole record over one bad/missing field — log a
            # warning and fall back to a defensive extraction straight from the
            # raw JSON, so key fields (name, address, coords, rubrics, category)
            # are still saved.
            logger.warning('Частичная запись (проблема валидации): %s',
                           '; '.join(errors))
            return self._extract_fallback(item)

        # Name, description
        if catalog_item.name_ex:
            data['name'] = catalog_item.name_ex.primary
            data['description'] = catalog_item.name_ex.extension
        elif catalog_item.name:
            data['name'] = catalog_item.name
        elif catalog_item.type in self._type_names:
            data['name'] = self._type_names[catalog_item.type]

        # Type
        data['type'] = catalog_item.type

        # Address
        data['address'] = catalog_item.address_name

        # Reviews
        if catalog_item.reviews:
            data['general_rating'] = catalog_item.reviews.general_rating
            data['general_review_count'] = catalog_item.reviews.general_review_count

        # Point location
        if catalog_item.point:
            data['point_lat'] = catalog_item.point.lat  # Latitude (широта)
            data['point_lon'] = catalog_item.point.lon  # Longitude (долгота)

        # Address comment
        data['address_comment'] = catalog_item.address_comment

        # Post code, building
        if catalog_item.address:
            data['postcode'] = catalog_item.address.postcode
            data['building_id'] = catalog_item.address.building_id
            data['building_name'] = catalog_item.address.building_name

        # Timezone
        if catalog_item.timezone is not None:
            data['timezone'] = catalog_item.timezone

        # Administrative location details
        for div in catalog_item.adm_div:
            for t in ('country', 'region', 'district_area', 'city', 'district', 'living_area'):
                if div.type == t:
                    data[t] = div.name

        # Item URL
        data['url'] = catalog_item.url

        # Organization / chain (network) info
        if catalog_item.org:
            data['branch_count'] = catalog_item.org.branch_count
            data['org_id'] = catalog_item.org.id
            data['org_name'] = catalog_item.org.primary or catalog_item.org.name
            data['org_specialization'] = catalog_item.org.extension

        # Primary (main) rubric — the one 2GIS marks as `kind == 'primary'`
        primary_rubric = next((x.name for x in catalog_item.rubrics
                               if x.kind == 'primary'), None)
        if primary_rubric:
            data['primary_rubric'] = primary_rubric

        # POI category (e.g. "fastfood", "bar")
        data['poi_category'] = catalog_item.poi_category

        # Object identity / administrative ids.
        # The part after "_" is an unstable per-response token, so we keep only
        # the stable firm id (same one used in the 2GIS URL) — good for dedup/counting.
        data['id'] = catalog_item.id.split('_')[0]
        data['floor_id'] = catalog_item.floor_id
        data['segment_id'] = catalog_item.segment_id
        data['region_id'] = catalog_item.region_id
        data['is_deleted'] = catalog_item.is_deleted

        # Functional-richness metrics
        data['rubric_count'] = len(catalog_item.rubrics)
        data['attributes_count'] = sum(len(g.attributes) for g in catalog_item.attribute_groups)

        # Last update date
        if catalog_item.dates:
            data['updated_at'] = catalog_item.dates.updated_at

        # Expected total count reported by 2GIS for the query (for verification)
        data['expected_count'] = self._expected_count

        # Source query URL (which parsed link this item came from)
        data['source_url'] = self._source_url

        # Contacts
        for contact_group in catalog_item.contact_groups:
            def append_contact(contact_type: str, priority_fields: list[str],
                               formatter: Callable[[str], str] | None = None) -> None:
                """Add contact to `data`.

                Args:
                    contact_type: Contact type (see `Contact` in `catalog_item.py`)
                    priority_fields: Field of contact to be added, sorted by priority
                    formatter: Field value formatter
                """
                contacts = [x for x in contact_group.contacts if x.type == contact_type]
                for i, contact in enumerate(contacts, 1):
                    contact_value = None

                    for field in priority_fields:
                        if hasattr(contact, field):
                            contact_value = getattr(contact, field)
                            break

                    # Empty contact value, bail
                    if not contact_value:
                        return

                    data_name = f'{contact_type}_{i}'
                    if data_name in data:
                        data[data_name] = formatter(contact_value) if formatter else contact_value

                        # Add comment on demand
                        if self._options.csv.add_comments and contact.comment:
                            data[data_name] += ' (%s)' % contact.comment

            # URLs
            for t in ['website', 'vkontakte', 'whatsapp', 'viber', 'telegram',
                      'instagram', 'facebook', 'twitter', 'youtube', 'skype']:
                append_contact(t, ['url'])

            # Remove arguments from WhatsApp URL
            for field in data:
                if field.startswith('whatsapp') and data[field]:
                    data[field] = data[field].split('?')[0]

            # Values
            for t in ['email', 'skype']:
                append_contact(t, ['value'])

            # Phone (`value` sometimes has strange crap inside, so we better parse `text`.
            # If no `text` field in contact - use `value` attribute)
            append_contact('phone', ['text', 'value'],
                           formatter=lambda x: re.sub(r'^\+7', '8', re.sub(r'[^0-9+]', '', x)))

        # Schedule
        if catalog_item.schedule:
            data['schedule'] = catalog_item.schedule.to_str(self._options.csv.join_char,
                                                            self._options.csv.add_comments)

        # Rubrics
        if self._options.csv.add_rubrics:
            data['rubrics'] = self._options.csv.join_char.join(x.name for x in catalog_item.rubrics)

        return data
