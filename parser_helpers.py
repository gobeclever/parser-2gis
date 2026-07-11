#!/usr/bin/env python3
"""Вспомогательные функции: генерация ссылок 2GIS и имён файлов
из города и rubricId. Данные берутся из parser_2gis/data/*.json.

Ничего в ядре парсера не меняет — это отдельный слой, который можно
импортировать в run_parse.py / make_urls.py.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
from functools import lru_cache

# Папка с данными (cities.json, rubrics.json) — рядом с этим файлом
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'parser_2gis', 'data')


@lru_cache(maxsize=1)
def load_cities() -> list:
    with open(os.path.join(DATA_DIR, 'cities.json'), encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_rubrics() -> dict:
    with open(os.path.join(DATA_DIR, 'rubrics.json'), encoding='utf-8') as f:
        return json.load(f)


def find_city(name_or_code: str) -> dict:
    """Найти город по коду ('moscow') или названию ('Москва')."""
    key = str(name_or_code).strip().lower()
    for c in load_cities():
        if c.get('code', '').lower() == key or c.get('name', '').lower() == key:
            return c
    raise ValueError(f'Город не найден: {name_or_code!r}. '
                     f'Укажи код (например "moscow") или название ("Москва").')


def rubric_label(rubric_id: str | int) -> str | None:
    """Название рубрики по её id (из rubrics.json)."""
    r = load_rubrics().get(str(rubric_id))
    return r['label'] if r else None


def encode_query(text: str) -> str:
    """Кодирование текста запроса как в 2GIS: русские буквы и пробелы
    остаются как есть, всё остальное percent-кодируется (в т.ч. '/' -> %2F)."""
    out = []
    for ch in text:
        o = ord(ch.lower())
        if 1072 <= o <= 1103 or o in (1105, 32):  # [а-я], ё, пробел
            out.append(ch)
        else:
            out.append(urllib.parse.quote(ch, safe=''))
    return ''.join(out)


def build_url(city: dict, rubric_id: str | int,
              label: str | None = None, sort_by_name: bool = True) -> str:
    """Собрать ссылку выдачи 2GIS для города и рубрики."""
    label = label or rubric_label(rubric_id) or ''
    url = f'https://2gis.{city["domain"]}/{city["code"]}/search/{encode_query(label)}'
    url += f'/rubricId/{rubric_id}'
    if sort_by_name:
        url += '/filters/sort=name'
    return url


def _sanitize(name: str) -> str:
    """Сделать строку пригодной для имени файла (кириллицу сохраняем)."""
    name = re.sub(r'[\\/:*?"<>|]+', '', name)   # убрать недопустимые символы
    name = re.sub(r'\s+', '_', name.strip())    # пробелы -> _
    name = re.sub(r'_+', '_', name)             # схлопнуть повторы _
    return name.strip('_')


def build_filename(city: dict, rubric_id: str | int,
                   label: str | None = None, ext: str = 'csv') -> str:
    """Имя файла вида city_rubricname_rubricID.ext (например moscow_Кафе_161.csv)."""
    label = label or rubric_label(rubric_id) or 'rubric'
    return f'{city["code"]}_{_sanitize(label)}_{rubric_id}.{ext.lstrip(".")}'
