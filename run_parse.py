#!/usr/bin/env python3
"""Запуск парсера из Python (без ввода команд в терминал).

Открой этот файл в VS Code и нажми "Run" (или запусти: python run_parse.py).
Меняй настройки ниже под свою задачу.
"""

from parser_2gis.config import Configuration
from parser_2gis.logger import setup_cli_logger
from parser_2gis.runner import CLIRunner

# ---------------------------------------------------------------------------
# 1. Что парсим (можно несколько ссылок — колонка "Ссылка запроса"
#    у каждой точки покажет, из какой именно она пришла).
URLS = [
    'https://2gis.ru/moscow/search/кафе/rubricId/161',
    # 'https://2gis.ru/moscow/search/аптеки',
]

# 2. Куда и в каком формате сохранить.
OUTPUT_PATH = 'test.xlsx'      # имя файла
FORMAT = 'xlsx'                # 'csv' | 'xlsx' | 'json' | 'jsonl'

# ---------------------------------------------------------------------------
# 3. Настройки. Всё опционально — что не тронешь, останется по умолчанию.
config = Configuration()

# Сколько записей максимум с одной ссылки.
config.parser.max_records = 20

# Удалять ли дубли (одна и та же точка). Для анализа рубрик ставь False,
# чтобы видеть все вхождения точки в разные рубрики.
config.writer.csv.remove_duplicates = False

# Удалять ли пустые колонки в конце.
config.writer.csv.remove_empty_columns = True

# Показывать окно браузера (False) или работать в фоне headless (True).
config.chrome.headless = False

# Отключить картинки в браузере — быстрее и меньше памяти (полезно для крупных рубрик).
config.chrome.disable_images = True

# Задержка между кликами по карточкам, мс. Ставь 100-300 для крупных прогонов,
# чтобы 2GIS не блокировал за частые запросы.
config.parser.delay_between_clicks = 0

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    setup_cli_logger(config.log)
    runner = CLIRunner(URLS, OUTPUT_PATH, FORMAT, config)
    runner.start()
    print(f'\nГотово. Результат: {OUTPUT_PATH}')
