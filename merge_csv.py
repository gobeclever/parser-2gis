#!/usr/bin/env python3
"""Объединение по-районных CSV в один файл на рубрику (вся Москва).

Берёт из папки ТОЛЬКО по-районные файлы (city_<район>_<рубрика>_<rid>.csv),
группирует их по rid и склеивает каждую группу в один файл
  city_all_<рубрика>_<rid>.csv .

По-районные файлы распознаются по префиксу с названием района (сверка с
districts.json), поэтому общегородские файлы других рубрик, лежащие в той же
папке, НЕ затрагиваются. Колонки «Район» и «Ссылка запроса» сохраняются.

Запуск: python merge_csv.py
"""
import csv
import glob
import os
import re
from collections import defaultdict

from parser_helpers import find_city, rubric_label, list_districts, _sanitize

# ============================ НАСТРОЙКИ ============================
INPUT_DIR = 'MLSD_moscow_zerkalo'     # папка с по-районными файлами
OUTPUT_DIR = INPUT_DIR                # куда класть объединённые файлы
CITY = 'moscow'                       # код города
RUBRIC_IDS = []                       # пусто = все найденные; иначе только эти rid, напр. ["350","373"]
DEDUP_BY_ID = False                   # True — убрать повторы по колонке "ID объекта"
ID_COLUMN = 'ID объекта'
ENCODING = 'utf-8-sig'
# ==================================================================


def main() -> None:
    city = find_city(CITY)
    code = city['code']

    # Префиксы, по которым узнаём по-районный файл: city_<санитайз(название района)>_
    prefixes = tuple(f'{code}_{_sanitize(d["name"])}_' for d in list_districts(code))
    if not prefixes:
        print(f'Нет списка районов для {code} в districts.json — не могу отличить '
              'по-районные файлы. Прерываю.')
        return

    groups = defaultdict(list)
    for path in glob.glob(os.path.join(INPUT_DIR, f'{code}_*.csv')):
        fn = os.path.basename(path)
        if fn.startswith(f'{code}_all_'):
            continue  # уже объединённые
        if not fn.startswith(prefixes):
            continue  # не по-районный файл (напр. общегородская другая рубрика) — пропуск
        # rid — это номер рубрики. В имени файла может быть несколько чисел
        # (напр. у двойных районов дописан district_id), поэтому берём самое
        # правое число, которое является реальной рубрикой из rubrics.json.
        nums = re.findall(r'_(\d+)(?=_|\.csv$)', fn)
        rid = next((n for n in reversed(nums) if rubric_label(n) is not None), None)
        if rid is None:
            m = re.search(r'_(\d+)\.csv$', fn)
            rid = m.group(1) if m else None
        if rid is None:
            continue
        if RUBRIC_IDS and rid not in RUBRIC_IDS:
            continue
        groups[rid].append(path)

    if not groups:
        print('По-районных файлов не найдено (проверь INPUT_DIR и CITY).')
        return

    for rid, paths in sorted(groups.items()):
        paths.sort()
        rname = rubric_label(rid) or rid
        out_name = f'{code}_all_{_sanitize(rname)}_{rid}.csv'
        out_path = os.path.join(OUTPUT_DIR, out_name)

        # 1-й проход: объединённый список колонок (на случай расхождений)
        fieldnames: list[str] = []
        seen_fn = set()
        for p in paths:
            with open(p, encoding=ENCODING, newline='') as fin:
                for col in (csv.DictReader(fin).fieldnames or []):
                    if col not in seen_fn:
                        seen_fn.add(col)
                        fieldnames.append(col)

        # 2-й проход: писать
        seen_ids = set()
        total = 0
        with open(out_path, 'w', encoding=ENCODING, newline='') as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            for p in paths:
                with open(p, encoding=ENCODING, newline='') as fin:
                    for row in csv.DictReader(fin):
                        if DEDUP_BY_ID:
                            v = row.get(ID_COLUMN)
                            if v and v in seen_ids:
                                continue
                            if v:
                                seen_ids.add(v)
                        writer.writerow(row)
                        total += 1
        print(f'{out_name}: {total} строк из {len(paths)} по-районных файлов')

    print(f'\nГотово. Объединённые файлы в: {os.path.abspath(OUTPUT_DIR)}')


if __name__ == '__main__':
    main()
