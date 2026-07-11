#!/usr/bin/env python3
"""Генератор ссылок 2GIS и имён файлов.

Укажи город и список rubricId — скрипт выведет готовые ссылки и
предлагаемые имена файлов. Ссылки можно скопировать в -i или в run_parse.py.

Запуск: python make_urls.py
"""
from parser_helpers import find_city, rubric_label, build_url, build_filename

# ---- настрой под себя ----
CITY = 'moscow'                 # код ('moscow') или название ('Москва')
RUBRIC_IDS = ['161', '159', '166', '367']   # список rubricId
EXT = 'csv'                     # для имени файла
# --------------------------

city = find_city(CITY)
print(f'Город: {city["name"]} ({city["code"]}.{city["domain"]})\n')
for rid in RUBRIC_IDS:
    name = rubric_label(rid)
    if name is None:
        print(f'[!] rubricId {rid} не найден в rubrics.json (обнови список или проверь id)')
        continue
    url = build_url(city, rid)
    fname = build_filename(city, rid, ext=EXT)
    print(f'{name} (id {rid})')
    print(f'  URL:  {url}')
    print(f'  файл: {fname}\n')
