#!/usr/bin/env python3
"""Запуск парсера из Python с авто-генерацией ссылок и имён файлов.

Ты указываешь: город, список rubricId, папку для результатов и настройки.
Для каждой рубрики скрипт сам:
  * собирает ссылку выдачи 2GIS,
  * формирует имя файла вида  city_rubricname_rubricID  (напр. moscow_Кафе_161.csv),
  * запускает парсер и сохраняет результат в указанную папку.

Открой в VS Code и нажми Run (или: python run_parse.py).
"""
import os

from parser_helpers import find_city, rubric_label, build_url, build_filename

from parser_2gis.config import Configuration
from parser_2gis.logger import setup_cli_logger, logger
from parser_2gis.runner import CLIRunner

# ============================ НАСТРОЙКИ ============================
CITY = 'moscow'                       # код ('moscow') или название ('Москва')
RUBRIC_IDS = ["373","350"]                  # список rubricId — по одному файлу на рубрику
OUTPUT_DIR = 'MLSD_moscow_zerkalo'                # папка для результатов (создастся, если нет)
FORMAT = 'csv'                        # 'csv' | 'xlsx' | 'json' | 'jsonl'

config = Configuration()
config.parser.max_records = 100000               # практически без ограничения
config.writer.csv.remove_duplicates = False       # не удалять дубли
config.writer.csv.remove_empty_columns = False
config.chrome.headless = False                    # True — работать в фоне без окна
config.chrome.disable_images = True
config.parser.delay_between_clicks = 450            # 100-300 для крупных прогонов
config.parser.use_gc = True
config.parser.gc_pages_interval = 5

config.parser.empty_page_retries = 1
config.parser.empty_page_retry_delay = 4000     # мс
config.parser.max_browser_restarts = 5          # 0 — выключить докачку
# ==================================================================

if __name__ == '__main__':
    setup_cli_logger(config.log)

    city = find_city(CITY)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for rid in RUBRIC_IDS:
        name = rubric_label(rid)
        if name is None:
            logger.warning('rubricId %s не найден в rubrics.json — пропуск', rid)
            continue

        url = build_url(city, rid)
        out_path = os.path.join(OUTPUT_DIR, build_filename(city, rid, ext=FORMAT))

        logger.info('=== %s (id %s) -> %s ===', name, rid, out_path)
        CLIRunner([url], out_path, FORMAT, config).start()

    print(f'\nГотово. Результаты в папке: {os.path.abspath(OUTPUT_DIR)}')
