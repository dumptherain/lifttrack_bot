import sqlite3

DB_PATH = 'workout_sessions.db'
SCHEMA_PATH = 'schema.sql'

def init_db(db_path, schema_path):
    with sqlite3.connect(db_path) as conn:
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())

def get_connection(db_path):
    return sqlite3.connect(db_path)
