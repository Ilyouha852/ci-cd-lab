import sqlite3
from pathlib import Path
from config import DATABASE_PATH

def get_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(DATABASE_PATH)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def init_db(seed=True):
    base=Path(__file__).parent
    with get_db() as db:
        db.executescript((base/'database/schema.sql').read_text(encoding='utf-8'))
        if seed and db.execute('SELECT COUNT(*) FROM owners').fetchone()[0]==0:
            db.executescript((base/'database/seed.sql').read_text(encoding='utf-8'))
        db.commit()
 