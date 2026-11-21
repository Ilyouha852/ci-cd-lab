import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))   # тесты запускаются из любой папки

import clients, config, database
from app import create_app

OWNERS = [
    {'id': 1, 'full_name': 'Иванов Иван Иванович'},
    {'id': 2, 'full_name': 'Петров Пётр Петрович'},
    {'id': 3, 'full_name': 'Сидорова Анна Сергеевна'},
]


@pytest.fixture()
def owners(monkeypatch):
    """Подмена owners-service: отвечает из списка OWNERS, сеть не нужна."""
    monkeypatch.setattr(clients, 'list_owners', lambda: OWNERS)
    monkeypatch.setattr(clients, 'get_owner', lambda i: next((o for o in OWNERS if o['id'] == int(i)), None))
    monkeypatch.setattr(clients, 'count_owners', lambda: len(OWNERS))


@pytest.fixture()
def owners_down(monkeypatch):
    """owners-service недоступен."""
    def boom(*a, **k):
        raise clients.OwnersUnavailable('down')
    for name in ('list_owners', 'get_owner', 'count_owners'):
        monkeypatch.setattr(clients, name, boom)


@pytest.fixture()
def client(tmp_path, monkeypatch, owners):
    dbfile = tmp_path / 'test.db'
    monkeypatch.setattr(config, 'DATABASE_PATH', dbfile)
    monkeypatch.setattr(database, 'DATABASE_PATH', dbfile)
    database.init_db()
    return create_app({'TESTING': True, 'SECRET_KEY': 'test'}).test_client()
