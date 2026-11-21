import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import clients, config, database
from app import create_app


@pytest.fixture()
def no_cars(monkeypatch):
    """cars-service отвечает: у владельца нет автомобилей."""
    monkeypatch.setattr(clients, 'count_cars', lambda owner_id: 0)


@pytest.fixture()
def client(tmp_path, monkeypatch, no_cars):
    dbfile = tmp_path / 'test.db'
    monkeypatch.setattr(config, 'DATABASE_PATH', dbfile)
    monkeypatch.setattr(database, 'DATABASE_PATH', dbfile)
    database.init_db()
    return create_app({'TESTING': True, 'SECRET_KEY': 'test'}).test_client()
