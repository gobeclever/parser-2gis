#!/usr/bin/env python3
# Диагностика: где на странице выдачи лежит число "Найдено N".
import os, sys, json

for _ in range(2):
    try:
        from parser_2gis.chrome import ChromeOptions, ChromeRemote
        break
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        parent = os.path.abspath(os.path.join(here, os.pardir))
        if parent not in sys.path:
            sys.path.insert(1, parent)

URL = 'https://2gis.ru/moscow/search/кафе/rubricId/161'
SEARCH_PATTERN = r'https://catalog\.api\.2gis\.[^/]+/[^/]+/items\?'

opts = ChromeOptions(headless=False)
with ChromeRemote(opts, [SEARCH_PATTERN]) as chrome:
    chrome.navigate(URL, referer='https://google.com', timeout=120)
    chrome.wait(4)

    # 1) Ищем все ключи 'total' внутри window.initialState с их путями
    js = r'''
        (function() {
            var out = [];
            function walk(o, path, depth) {
                if (depth > 8 || o === null || typeof o !== 'object') return;
                for (var k in o) {
                    try {
                        var v = o[k];
                        if (k === 'total' && (typeof v === 'number')) {
                            out.push(path + '.total = ' + v);
                        }
                        if (v && typeof v === 'object') walk(v, path + '.' + k, depth + 1);
                    } catch(e) {}
                }
            }
            try { walk(window.initialState, 'initialState', 0); } catch(e) { return 'NO initialState: ' + e; }
            return out.slice(0, 40).join('\n');
        })();
    '''
    res = chrome.execute_script(js)
    print('=== "total" ключи в window.initialState ===')
    print(res if res else '(ничего не найдено)')

    # 2) Пробуем поймать сетевой ответ items? (может не прийти на 1-й странице)
    print()
    print('=== сетевой ответ items? ===')
    resp = chrome.wait_response(SEARCH_PATTERN)
    if resp and resp.get('status', -1) >= 0:
        body = chrome.get_response_body(resp)
        try:
            total = json.loads(body)['result']['total']
            print('items? result.total =', total)
        except Exception as e:
            print('поймал ответ, но total не извлёкся:', e)
    else:
        print('сетевой ответ items? НЕ пойман на первой странице (ожидаемо, если выдача серверная)')
