"""HTTP-клиент к cars-service.

Нужен для одной проверки: нельзя удалить владельца, у которого есть автомобили.
В одной БД это делал внешний ключ ON DELETE RESTRICT, между сервисами его нет.
"""
import json
import urllib.error
import urllib.request

import config


class CarsUnavailable(Exception):
    """cars-service не ответил или ответил ошибкой сервера."""


def count_cars(owner_id):
    url = f'{config.CARS_SERVICE_URL}/api/cars/count?owner_id={int(owner_id)}'
    try:
        with urllib.request.urlopen(url, timeout=config.CARS_TIMEOUT) as resp:
            return int(json.load(resp)['count'])
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        raise CarsUnavailable(f'cars-service недоступен: {e}') from e
