import sqlite3
from pathlib import Path
from contextlib import contextmanager

AUTH_SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY,username TEXT NOT NULL UNIQUE COLLATE NOCASE,name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN('Admin','Petugas')),password TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,count INTEGER NOT NULL,until INTEGER NOT NULL);
'''

def connect(folder):
    directory = Path(folder)
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / 'app.sqlite', timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    return db

def initialize(folder, schema=''):
    db = connect(folder)
    try:
        db.executescript(AUTH_SCHEMA + schema)
    finally:
        db.close()

@contextmanager
def transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
