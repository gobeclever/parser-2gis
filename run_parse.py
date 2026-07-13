#!/usr/bin/env python3
"""Запуск парсера из Python с авто-генерацией ссылок и имён файлов.

Два режима:
  * SPLIT_BY_DISTRICT = False — один файл на рубрику по всему городу
        (имя: city_rubricname_rubricID, напр. moscow_Кафе_161.csv).
  * SPLIT_BY_DISTRICT = True  — рубрика дробится по районам: один файл на
        (район × рубрика). Нужно для рубрик-гигантов (супермаркеты и т.п.),
        которые целиком не влезают в потолок выдачи 2GIS (~9000). Имя:
        city_district_rubricname_rubricID, напр. moscow_Академический_Супермаркеты_350.csv.

Открой в VS Code и нажми Run (или: python run_parse.py).
"""
import os

from parser_helpers import (find_city, rubric_label, build_url, build_filename,
                            list_districts, build_district_url, build_district_filename)

from parser_2gis.config import Configuration
from parser_2gis.logger import setup_cli_logger, logger
from parser_2gis.runner import CLIRunner

# ============================ НАСТРОЙКИ ============================
CITY = 'moscow'                       # код ('moscow') или название ('Москва')
RUBRIC_IDS = ["373", "350"]           # список rubricId
OUTPUT_DIR = 'MLSD_moscow_zerkalo'    # папка для результатов (создастся, если нет)
FORMAT = 'csv'                        # 'csv' | 'xlsx' | 'json' | 'jsonl'

SPLIT_BY_DISTRICT = True              # True — дробить по районам (для гигантов); False — город целиком
SKIP_EXISTING = True                  # пропускать уже готовые файлы (удобно для докачки большого прогона)

config = Configuration()
config.parser.max_records = 100000               # практически без ограничения
config.writer.csv.remove_duplicates = False       # не удалять дубли
config.writer.csv.remove_empty_columns = False
config.chrome.headless = False                    # True — работать в фоне без окна
config.chrome.disable_images = True
config.parser.delay_between_clicks = 150            # 100-300 для крупных прогонов
config.parser.use_gc = True
config.parser.gc_pages_interval = 5

config.parser.empty_page_retries = 1
config.parser.empty_page_retry_delay = 4000     # мс
config.parser.max_browser_restarts = 5          # 0 — выключить докачку
# ==================================================================


def run_one(url: str, out_path: str, title: str) -> None:
    if SKIP_EXISTING and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        logger.info('Пропуск (файл уже есть): %s', out_path)
        return
    logger.info('=== %s -> %s ===', title, out_path)
    CLIRunner([url], out_path, FORMAT, config).start()


if __name__ == '__main__':
    setup_cli_logger(config.log)

    city = find_city(CITY)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for rid in RUBRIC_IDS:
        name = rubric_label(rid)
        if name is None:
            logger.warning('rubricId %s не найден в rubrics.json — пропуск', rid)
            continue

        if SPLIT_BY_DISTRICT:
            districts = list_districts(city['code'])
            if not districts:
                logger.warning('Нет списка районов для %s — беру город целиком.', city['code'])
                run_one(build_url(city, rid),
                        os.path.join(OUTPUT_DIR, build_filename(city, rid, ext=FORMAT)),
                        f'{name} (id {rid})')
                continue

            logger.info('Рубрика "%s" (id %s): дробление по %s районам.', name, rid, len(districts))
            seen_names: set[str] = set()
            for d in districts:
                dname = d['name']
                fname = build_district_filename(city, rid, dname, ext=FORMAT)
                if fname in seen_names:
                    # Разные районы с одинаковым названием (напр. два «Северный»)
                    # — уникализируем сам район его id, при этом номер рубрики
                    # остаётся в конце имени файла (важно для merge_csv).
                    dname = f'{d["name"]} {d["id"]}'
                    fname = build_district_filename(city, rid, dname, ext=FORMAT)
                seen_names.add(fname)
                url = build_district_url(city, rid, d['id'])
                run_one(url, os.path.join(OUTPUT_DIR, fname), f'{name} / {d["name"]}')
        else:
            run_one(build_url(city, rid),
                    os.path.join(OUTPUT_DIR, build_filename(city, rid, ext=FORMAT)),
                    f'{name} (id {rid})')

    print(f'\nГотово. Результаты в папке: {os.path.abspath(OUTPUT_DIR)}')
