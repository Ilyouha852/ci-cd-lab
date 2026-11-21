"""HTTP-клиент к owners-service.

cars-service не имеет доступа к БД владельцев и общается с owners-service только
по его REST API. Любая сетевая ошибка превращается в OwnersUnavailable, чтобы
вызывающий код мог деградировать, а не падать с 500.
"""
import json
import urllib.error
import urllib.request

import config


class OwnersUnavailable(Exception):
    """owners-service не ответил или ответил ошибкой сервера."""


def _get(path):
    url = config.OWNERS_SERVICE_URL + path
    try:
        with urllib.request.urlopen(url, timeout=config.OWNERS_TIMEOUT) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:      # HTTPError раньше URLError: это его подкласс
        if e.code == 404:
            return None
        raise OwnersUnavailable(f'owners-service вернул {e.code}') from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise OwnersUnavailable(f'owners-service недоступен: {e}') from e


def list_owners():
    """Список владельцев: [{'id':1,'full_name':...}, ...]."""
    return _get('/api/owners') or []


def get_owner(owner_id):
    """Владелец по id или None, если такого нет."""
    return _get(f'/api/owners/{int(owner_id)}')


def count_owners():
    return _get('/api/owners/count')['count']
