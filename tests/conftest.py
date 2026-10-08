import pytest
from pathlib import Path
import config,database
from app import create_app
@pytest.fixture()
def client(tmp_path,monkeypatch):
    dbfile=tmp_path/'test.db'; monkeypatch.setattr(config,'DATABASE_PATH',dbfile); monkeypatch.setattr(database,'DATABASE_PATH',dbfile)
    with database.get_db() as db:
        db.executescript(Path('database/schema.sql').read_text(encoding='utf-8')); db.executescript(Path('database/seed.sql').read_text(encoding='utf-8')); db.commit()
    return create_app({'TESTING':True,'SECRET_KEY':'test'}).test_client()
 